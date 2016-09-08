# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from plone.app.event.base import _prepare_range
from plone.app.event.base import construct_calendar
from plone.app.event.base import expand_events
from plone.app.event.base import first_weekday
from plone.app.event.base import get_events
from plone.app.event.base import localized_today
from plone.app.event.base import RET_MODE_OBJECTS
from plone.app.event.base import start_end_query
from plone.app.event.base import wkday_to_mon1
from plone.app.event.portlets import get_calendar_url
from plone.app.querystring import queryparser
from plone.app.uuid.utils import uuidToObject
from plone.event.interfaces import IEventAccessor
from Products.CMFCore.utils import getToolByName
from zope.component.hooks import getSite
from zope.i18nmessageid import MessageFactory

import calendar
import json


try:
    from plone.app.contenttypes.behaviors.collection import ISyndicatableCollection as ICollection  # noqa
except ImportError:
    ICollection = None


PLMF = MessageFactory('plonelocales')


class CalendarMixin:
    _search_base = None

    @property
    def search_base(self):
        if not self._search_base:
            self._search_base = uuidToObject(self.data.search_base_uid)
        # aq_inner, because somehow search_base gets wrapped by the renderer
        return aq_inner(self._search_base)

    @property
    def search_base_path(self):
        search_base = self.search_base
        if search_base is not None:
            search_base = '/'.join(search_base.getPhysicalPath())
        return search_base

    def setup(self):
        context = aq_inner(self.context)

        self.calendar_url = get_calendar_url(context, self.search_base_path)

        self.year, self.month = year, month = self.year_month_display()
        self.prev_year, self.prev_month = prev_year, prev_month = (
            self.get_previous_month(year, month))
        self.next_year, self.next_month = next_year, next_month = (
            self.get_next_month(year, month))
        self.prev_query = '?month=%s&year=%s' % (prev_month, prev_year)
        self.next_query = '?month=%s&year=%s' % (next_month, next_year)

        self.cal = calendar.Calendar(first_weekday())
        self._ts = getToolByName(context, 'translation_service')
        self.month_name = PLMF(
            self._ts.month_msgid(month),
            default=self._ts.month_english(month)
        )

        # strftime %w interprets 0 as Sunday unlike the calendar.
        strftime_wkdays = [
            wkday_to_mon1(day) for day in self.cal.iterweekdays()
        ]
        self.weekdays = [
            PLMF(self._ts.day_msgid(day, format='s'),
                 default=self._ts.weekday_english(day, format='a'))
            for day in strftime_wkdays
        ]

    def year_month_display(self):
        """ Return the year and month to display in the calendar.
        """
        context = aq_inner(self.context)
        request = self.request

        # Try to get year and month from request
        year = request.get('year', None)
        month = request.get('month', None)

        # Or use current date
        today = localized_today(context)
        if not year:
            year = today.year
        if not month:
            month = today.month

        # try to transform to number but fall back to current
        # date if this is ambiguous
        try:
            year, month = int(year), int(month)
        except (TypeError, ValueError):
            year, month = today.year, today.month

        return year, month

    def get_previous_month(self, year, month):
        if month == 0 or month == 1:
            month, year = 12, year - 1
        else:
            month -= 1
        return (year, month)

    def get_next_month(self, year, month):
        if month == 12:
            month, year = 1, year + 1
        else:
            month += 1
        return (year, month)

    def date_events_url(self, date):
        return '%s?mode=day&date=%s' % (self.calendar_url, date)

    @property
    def cal_data(self):
        """Calendar iterator over weeks and days of the month to display.
        """
        context = aq_inner(self.context)
        today = localized_today(context)
        year, month = self.year_month_display()
        monthdates = [dat for dat in self.cal.itermonthdates(year, month)]

        start = monthdates[0]
        end = monthdates[-1]

        data = self.data
        query = {}
        if data.state:
            query['review_state'] = data.state

        events = []
        query.update(self.request.get('contentFilter', {}))
        search_base = self.search_base
        if ICollection and ICollection.providedBy(search_base):
            # Whatever sorting is defined, we're overriding it.
            query = queryparser.parseFormquery(
                search_base, search_base.query,
                sort_on='start', sort_order=None
            )

            # restrict start/end with those from query, if given.
            if 'start' in query and query['start'] > start:
                start = query['start']
            if 'end' in query and query['end'] < end:
                end = query['end']

            start, end = _prepare_range(search_base, start, end)
            query.update(start_end_query(start, end))
            events = search_base.results(
                batch=False, brains=True, custom_query=query
            )
            events = expand_events(
                events, ret_mode=RET_MODE_OBJECTS,
                start=start, end=end,
                sort='start', sort_reverse=False
            )
        else:
            search_base_path = self.search_base_path
            if search_base_path:
                query['path'] = {'query': search_base_path}
            events = get_events(context, start=start, end=end,
                                ret_mode=RET_MODE_OBJECTS,
                                expand=True, **query)

        cal_dict = construct_calendar(events, start=start, end=end)

        # [[day1week1, day2week1, ... day7week1], [day1week2, ...]]
        caldata = [[]]
        for dat in monthdates:
            if len(caldata[-1]) == 7:
                caldata.append([])
            date_events = None
            isodat = dat.isoformat()
            if isodat in cal_dict:
                date_events = cal_dict[isodat]

            events_string = u""
            if date_events:
                for occ in date_events:
                    accessor = IEventAccessor(occ)
                    location = accessor.location
                    whole_day = accessor.whole_day
                    time = accessor.start.time().strftime('%H:%M')
                    # TODO: make 24/12 hr format configurable
                    base = u'<a href="%s"><span class="title">%s</span>'\
                           u'%s%s%s</a>'
                    events_string += base % (
                        accessor.url,
                        accessor.title,
                        u' %s' % time if not whole_day else u'',
                        u', ' if not whole_day and location else u'',
                        u' %s' % location if location else u'')

            caldata[-1].append(
                {'date': dat,
                 'day': dat.day,
                 'prev_month': dat.month < month,
                 'next_month': dat.month > month,
                 'today':
                    dat.year == today.year and
                    dat.month == today.month and
                    dat.day == today.day,
                 'date_string': u"%s-%s-%s" % (dat.year, dat.month, dat.day),
                 'events_string': events_string,
                 'events': date_events})
        return caldata

    def nav_pattern_options(self, year, month):
        return json.dumps({
            'url': '%s/@@render-portlet?portlethash=%s&year=%s&month=%s' % (
                getSite().absolute_url(),
                self.hash,
                year, month),
            'target': '#portletwrapper-%s > *' % self.hash
        })

    @property
    def hash(self):
        return self.request.form.get(
            'portlethash',
            getattr(self, '__portlet_metadata__', {}).get('hash', ''))
