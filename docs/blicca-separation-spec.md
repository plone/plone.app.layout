# Plone Headless Stack: Blicca Separation Spec

Sep 26, 2026 · @Kombinat Media Gestalter GmbH

## Goal and scope

Plone 7 core packages contain no Blicca (Classic UI) templates, viewlets, portlets or view logic; all of it lives in `plone.app.layout` or in core-addons. This separation is the precondition for a headless Plone, but completing the headless stack is out of scope (D6). Tracked in [PLIP #3953](https://github.com/plone/Products.CMFPlone/issues/3953).

- **In scope:** page templates (`.pt`), `browser:page` / `browser:view` / viewlet / viewlet manager / menu registrations, and the Python view classes behind them, in every package that `Products.CMFPlone` or `plone.distribution` pulls in.
- **Documented only (D9):** `install_requires` of core packages: the edges that pull in Blicca packages are recorded, but removing them is out of scope.
- **Out of scope:** ZMI templates (Zope, PAS, GenericSetup, CMFCore, ZCatalog, …), generic frameworks (`z3c.form`, `zope.viewlet`), API views used by `plone.restapi` or by Zope traversal (`@@images`, `@@download`).

## Locked decisions

These decisions are fixed. Changes need agreement in the PLIP.

1. **D1 – Tracking:** [PLIP #3953](https://github.com/plone/Products.CMFPlone/issues/3953) is the single tracking issue. Its description lists every affected package and every dependent PR, each with a checkbox for completeness.
2. **D2 – Target package:** `plone.app.layout` is the target for all Blicca templates and view logic moved out of core packages.
3. **D3 – Core-addons stay as they are:** a package marked *core-addon* keeps its templates. Nothing moves to `plone.app.layout`.
4. **D4 – Known core-addons:** `plone.app.z3cform` (template layer for `plone.z3cform`), `plone.app.event` (template layer for `plone.event`) and `plone.app.portlets` (optional core-addon).
5. **D5 – REST API split:** where `plone.restapi` reuses view logic as API logic, that logic is split out. The API part stays in the core package, the template part moves to `plone.app.layout`.
6. **D6 – Scope:** this spec covers only the separation of Blicca (Classic UI) templates and view logic from core packages. Completing a headless Plone stack is out of scope.
7. **D7 – Versioning:** removing templates from a source package requires a new major version of that package. The work targets Plone 6.3 and later.
8. **D8 – Target branch:** `plone.app.layout` `master` (currently in 7.0 alpha) is the target for all moved views.
9. **D9 – Dependencies:** the dependency restructuring is documented in this spec, but its implementation is out of scope.
10. **D10 – Widget templates:** widget templates of core packages move to `plone.app.z3cform`, the widget template layer (D4), not to `plone.app.layout`. First case: `plone.schema` (`email_display.pt`, `uri_display.pt`).

## Package categories

Every package in the headless dependency closure gets exactly one category. The category decides what has to happen to its templates and to its place in `install_requires`.

| Category | Definition | Templates / views | Who may depend on it |
| --- | --- | --- | --- |
| **Core** | Needed for a headless site: content, workflow, security, catalog, registry, API | None for Blicca. Allowed: API views, ZMI templates, traversal views (`@@images`, `@@download`) | Anyone |
| **Core (split)** | Core package whose view logic is reused by `plone.restapi` (D5) | API logic stays; templates and HTML views move to `plone.app.layout` | Anyone |
| **Blicca** | `plone.app.layout` and packages that only exist for Classic UI (theming, static resources, viewlets) | Keep all templates; `plone.app.layout` receives the moved ones (D2) | `plone.classicui` and other Blicca or core-addon packages only |
| **Core-addon** | Optional package with its own template layer (D3, D4) | Keep their templates, nothing moves | The `Plone` meta package or the integrator; never `plone.classicui` or a core package |
| **Out of scope** | ZMI-only templates and generic frameworks | Unchanged | Anyone |

Rule of thumb: after the PLIP, a core package contains no Blicca template or view outside the allowlist; its `install_requires` stay unchanged (D9).

## Package inventory

23 core packages still need work or a check; 9 of them are not yet listed in the PLIP. Counts are non-test templates / `browser:page` registrations in the versions installed in `buildout.coredev` 6.3 (`Products.CMFPlone` from `master`); unreleased PR branches are not included.

### Core packages: action required

| Package | Category | Templates / pages | Action | In PLIP | Status |
| --- | --- | --- | --- | --- | --- |
| Products.CMFPlone | Core | 77 / 110 | Move all Blicca views to `plone.app.layout`; 10 templates moved in the draft PRs, 66 templates / 100 pages left (see breakdown below) | yes | In progress |
| plone.app.content | Core | 15 / 35 | Move templates; decide on the JSON views used by mockup (`@@getVocabulary`, `fc-*`) | yes |  |
| plone.app.contenttypes | Core | 14 / 26 | Move listing and content views | yes |  |
| Products.CMFEditions | Core | 25 (19 ZMI) / 12 | Move the 6 non-ZMI templates | yes |  |
| plone.app.dexterity | Core | 10 / 15 | Move templates and views: [plone.app.dexterity#431](https://github.com/plone/plone.app.dexterity/pull/431), [plone.app.layout#441](https://github.com/plone/plone.app.layout/pull/441); follow-up: the control panel schemas and the configlet (see [below](#plonedexterity-and-ploneappdexterity)) | yes | In progress |
| plone.app.users | Core | 8 / 11 | Move templates; drop the dependency on `plone.app.event` | yes |  |
| plone.schema | Core | 2 / 0 | Move `email_display.pt` and `uri_display.pt` to `plone.app.z3cform` (D10): [plone.schema#71](https://github.com/plone/plone.schema/pull/71), [plone.app.z3cform#290](https://github.com/plone/plone.app.z3cform/pull/290) | yes | In progress |
| plone.protect | Core | 1 / 2 | Move the `confirm.pt` view | yes |  |
| plone.app.registry | Core | 0 / 0 | – | yes | Done |
| plone.app.i18n | Core | 0 / 0 | – | yes | Done |
| plone.app.workflow | Core | 0 / 1 | Check that the remaining page is API | yes |  |
| plone.app.linkintegrity | Core | 0 / 1 | Check that the remaining page is API | yes |  |
| plone.locking | Core | 0 / 3 | Check that the remaining pages are API | yes |  |
| plone.dexterity | Core | 4 / 5 | Move the default `view`, `edit`, `add`, `content-core` views and their 3 templates; `plone.dexterity.fti` (`fti.pt`) is the ZMI add form and stays | no | Todo |
| plone.schemaeditor | Core (split) | 3 / 8 | Keep the schema logic used by `@types`; move the TTW editor UI | no | Todo |
| plone.app.querystring | Core (split) | 1 / 5 | Keep `querybuilderresults`, `querybuilderjsonconfig`; move `results.pt`, `querybuilder_html_results`, `display_query_results` | no | Todo |
| plone.batching | Core (split) | 3 / 2 | Keep `Batch`; move `batchnavigation`, `batch_macros` | no | Todo |
| plone.app.textfield | Core | 3 / 1 | None: widget templates stay in the package (too much logic to move) | no | Todo |
| plone.formwidget.namedfile | Core | 4 / 1 | None: templates stay in the package | no | Not needed |
| plone.app.versioningbehavior | Core | 2 / 2 | Move `version-view`; check `download-version` | no | Todo |
| plone.app.vocabularies | Core (split) | 1 / 0 | Core, because `plone.restapi` uses its vocabularies (`@types`, `@vocabularies`); move `searchabletextsource.pt` to `plone.app.layout` | optional | Not needed |
| plone.app.redirector | Core | 0 / 1 | `plone_redirector_view` only serves the Blicca 404 page | no | Todo |
| plone.app.contentlisting | Core | 0 / 3 | Check whether `contentlisting` / `folderListing` are only used by Blicca templates | no | Todo |

### Products.CMFPlone breakdown

The draft PRs [Products.CMFPlone#4378](https://github.com/plone/Products.CMFPlone/pull/4378) / [plone.app.layout#461](https://github.com/plone/plone.app.layout/pull/461) move 10 templates; 66 non-test templates and 100 active page registrations are still in CMFPlone. Scan of the PR branch on 2026-09-27; commented-out ZCML is not counted. Each area is a candidate for its own PR pair.

Already moved: accessibility-info, author, author\_feedback\_template, colophon, contact-info (+ mail template), footer, recently\_modified, recently\_published, toolbar.

| Area | Templates | Pages | Contents | Action |
| --- | --: | --: | --- | --- |
| Page frame and rendering | 15 | 17 | `main_template` (+ ajax / five), `title`, `description`, `global_statusmessage`, error view `index.html` for `Exception` (+ 2 error templates), `sitemap`, `search`, `ajax-search`, `sendto_form`, `test-rendering*` (4), `plone`, `iconresolver`, `plone_patterns_settings` | Move to `plone.app.layout` |
| Login and password | 17 | 18 | `login`, `login_form`, `failsafe_login`, `login-help`, `logged-out`, `insufficient-privileges`, `require_login`, `logout`, password reset (`mail_password*`, `pwreset_*`, `passwordreset`), `forced-password-change`, `initial-login-password-change`, `registered_notify_template` | Split (D5): `plone.restapi` uses the `login` view (`@login`); `require_login` is the PAS challenge target |
| Control panels | 21 | 43 | All `*-controlpanel` pages, users and groups, error log, add-ons (`prefs_install_products_form`, …), `redirection-controlpanel` / `manage-aliases`, `inspect-relations` / `rebuild-relations`, actions, `resourceregistry` | Split (D5): `plone.restapi` uses `overview-controlpanel`, `prefs_install_products_form`, `RedirectsControlPanel`, `RedirectionSet`, `absolutize_path` |
| Syndication | 7 | 8 | `rss.xml`, `atom.xml`, `RSS`, `itunes.xml`, `newsml.xml`, `search_rss`, `synPropertiesForm`, `syndication-util` | Open question |
| Zope root admin | 5 | 7 | `plone-overview`, `plone-addsite`, `plone-upgrade`, `plone-frontpage-setup`, `plone-root-login` / `plone-root-logout` | Open question |
| API and helper views | – | 8 | `breadcrumbs_view`, `portal_tabs_view`, `sitemap_builder_view`, `robots.txt`, `ok`, `favicon.ico`, `site-logo`, `default_page` | Stay; navigation logic stays as API (REST API split) |
| Resource viewlets | – | 2 viewlets | `plone.resourceregistries.scripts`, `plone.resourceregistries.styles` | Move to `plone.app.layout` |
| ZMI (`www/`) | 4 | – | `addConfigletForm.pt` + 3 DTML | Out of scope |
| CMF skin layers (`skins/`, `profiles/default/skins.xml`) | 1 | – | `plone_wysiwyg/wysiwyg_support.pt`, 8 skin scripts in `plone_scripts` (`browserDefault`, `pretty_title_or_id`, `toLocalizedTime`, `translate`, `utranslate`, `unique`, `external_edit`, `externalEditorEnabled`), 53 images in `plone_images` | Open question; not covered by the acceptance scans |

### Packages that keep their templates

| Package | Category | Templates | Note |
| --- | --- | --- | --- |
| plone.app.layout | Blicca (target) | 49 | Receives all moved views (D2) |
| plone.app.z3cform | Core-addon (D4) | 29 | Template layer for `plone.z3cform`; receives the `plone.schema` widget templates (D10) |
| plone.app.event | Core-addon (D4) | 7 | Template layer for `plone.event`; brings `plone.formwidget.recurrence` |
| plone.app.portlets | Core-addon (D4) | 30 | Together with `plone.portlets`, `plone.portlet.static`, `plone.portlet.collection` |
| plone.app.theming, plone.resourceeditor, plonetheme.barceloneta, plone.staticresources | Blicca | 4 | Theming stack |
| plone.app.contentmenu, plone.app.viewletmanager, plone.app.customerize, five.customerize, plone.theme | Blicca | 9 | PLIP: optional |
| plone.outputfilters | Blicca | 1 | PLIP: Classic UI only |
| plone.app.contentrules, plone.stringinterp | Core-addon (proposed) | 5 | PLIP: optional, deprecation candidate for Plone 7 |
| plone.session | open | 2 | PLIP: optional |
| plone.namedfile | Core (keep) | 0 | `@@images`, `@@download`, `@@display-file` are API |
| plone.distribution | Core (keep) | 1 | Site creation at the Zope root, needed headless too |
| z3c.form, plone.z3cform, zope.viewlet | Out of scope | – | Generic frameworks |
| Zope, PAS, GenericSetup, CMFCore, DCWorkflow, ZCatalog, PortalTransforms, MimetypesRegistry, PlonePAS, CMFDynamicViewFTI, … | Out of scope | – | ZMI templates only |

### plone.dexterity and plone.app.dexterity

Checked on 2026-09-28 while preparing the plone.app.dexterity PR pair. Question: can `plone.app.dexterity` be dissolved into `plone.dexterity` once its views are gone? Answer: not without breaking D4, so both packages stay; their roles are sharpened instead.

**What stays in `plone.app.dexterity` after the move** (6.0.0, PR branch): the 13 standard behaviors (`plone.basic`, `plone.dublincore`, `plone.publication`, `plone.ownership`, `plone.namefromtitle`, `plone.namefromfilename`, `plone.navigationroot`, `plone.excludefromnavigation`, `plone.nextprevioustoggle`, `plone.nextpreviousenabled`, `plone.constraintypes`, `plone.shortname`, `plone.categorization`), the `textindexer` (SearchableText behavior, converters, schema editor extender), `DXFileFactory`, the field permission checkers, `serialize`, the GenericSetup profiles `default` (configlet `dexterity-types`) and `testing`, 8 upgrade steps, and the control panel schemas `ITypeSettings`, `ITypeStats`, `ITypesContext`, `ITypeSchemaContext` with their validators. Its ZCML also declares `ILocalPortletAssignable`, `IRuleAssignable` and `IImageScaleTraversable` on `DexterityContent`.

**`plone.dexterity`** (4.0.0) is the framework: FTI, content classes, schema handling, `plone.behavior` integration. It is not a pure backend either: it depends on `plone.base`, `z3c.form` and `Products.statusmessages`, and registers the default `view`, `edit`, `add` and `content-core` views with 3 templates (inventory row above). `fti.pt` is the ZMI add form (out of scope).

**Why a merge is out**

| Finding | Consequence |
| --- | --- |
| The metadata behaviors bind `AjaxSelectFieldWidget` and `Select2FieldWidget`, and `permissions.py` builds on `IFieldPermissionChecker`, both from `plone.app.z3cform` | `plone.dexterity` would gain a hard dependency on a core-addon (D4) |
| `plone.namedfile` and `plone.app.relationfield` require `plone.dexterity`; `plone.app.dexterity` needs both (`DXFileFactory`, namedfile converter, `IRelatedItems`) | Two dependency cycles after a merge; today they are avoided because `plone.app.dexterity` sits above both |
| Behavior dotted names (`plone.app.dexterity.behaviors.metadata.IDublinCore`, …) are persisted in every site's `portal_types`; the profile `plone.app.dexterity:default` is a dependency of other profiles (plone.api, plone.exportimport, …) | Permanent BBB aliases and a profile alias would be required |
| 12 distributions require `plone.app.dexterity`; the most imported symbols are `IBasic`, the message factory `_`, `ICategorization`, `IPublication`, `INextPreviousProvider` and the `textindexer`. `plone.restapi` uses `IPublication`, `INextPreviousProvider` and the `textindexer`, `plone.volto` the message factory | Wide blast radius for a package rename |

**Follow-ups within the PLIP**

- Move `ITypeSettings`, `ITypeStats`, `ITypesContext`, `ITypeSchemaContext`, the validators and the configlet in `profiles/default/controlpanel.xml` to `plone.app.layout` with BBB aliases: they belong to the views moved in [plone.app.layout#441](https://github.com/plone/plone.app.layout/pull/441).
- Move the `plone.dexterity` default views (inventory row).
- The widget directives in the behaviors are the real coupling to `plone.app.z3cform`. Replacing them by `IFieldWidget` adapters registered in `plone.app.z3cform` would free `plone.app.dexterity` from the core-addon; this is outside the PLIP (D9 spirit: documented, not implemented).

## REST API split

`plone.restapi` reuses view logic from 14 packages today and even lists `plone.app.layout` in its `install_requires`. Both block a headless install, so every reuse below is split per D5.

**Split rule**

1. API logic moves to a non-`browser` module of the core package (function, utility or adapter). It must not render HTML or depend on a template.
2. The Blicca view in `plone.app.layout` calls that API. The old import path keeps a BBB alias until Plone 8.
3. `plone.restapi` calls the API directly, never a view by name.
4. Reuse of a *core-addon* view is registered conditionally (`zcml:condition="installed …"`), so the endpoint only exists when the add-on is installed.

**Reuse found in `plone.restapi`** (grep of `getMultiAdapter` / `queryMultiAdapter` names and `browser` imports, tests excluded)

| Reused view or symbol | Provided by | Endpoints | Action |
| --- | --- | --- | --- |
| `plone_portal_state` (25 uses), `plone_context_state` | plone.app.layout (Blicca) | 17 modules: `@site`, `@navigation`, `@breadcrumbs`, `@actions`, `@types`, … | None for now: the state views stay in `plone.app.layout` |
| `ContentHistoryViewlet` | plone.app.layout (Blicca) | `@history` | Extract the history logic into a core API (CMFEditions) |
| `@@delete_confirmation_info` | plone.app.layout, plone.app.linkintegrity | `@linkintegrity` | Keep the breach logic in plone.app.linkintegrity as API |
| `breadcrumbs_view`, `portal_tabs_view`, `SitemapNavtreeStrategy` | Products.CMFPlone | `@breadcrumbs`, `@navigation`, `@contextnavigation` | Keep navigation logic in core, move only HTML views |
| `login`, `contact-info`, `overview-controlpanel`, `prefs_install_products_form`, `Upgrade`, `RedirectsControlPanel`, `RedirectionSet`, `absolutize_path` | Products.CMFPlone | `@login`, `@email-notification`, `@email-send`, `@addons`, `@upgrade`, `@aliases`, `@site` | Extract logic from `browser` / `controlpanel.browser` modules |
| `dexterity-types`, `behaviors`, `add-type`, `overview`, `edit` | plone.app.dexterity | `@types`, `@controlpanels/dexterity-types` | Extract type and behavior management into API functions |
| `add-field`, `add-fieldset`, `order`, `delete`, `edit` | plone.schemaeditor | `@types` | Extract field and fieldset management into API functions |
| `register`, `getUserDataSchema`, `getRegisterSchema`, `applySchema` | plone.app.users | `@users`, `@userschema` | Move the schema helpers out of `browser` |
| `sharing`, `merge_search_results` | plone.app.workflow | `@sharing`, `@principals`, `@users` | Check that the sharing logic is API after the PLIP work |
| `PERMISSIONS`, `DEFAULT_PERMISSION` | plone.app.content (`browser.vocabulary`) | `@vocabularies`, content and schema serializers | Move constants out of `browser` |
| `querybuilderresults` | plone.app.querystring | `@querystring-search` | Keep in core (see inventory) |
| `images`, `USE_DENYLIST`, inline MIME type lists | plone.namedfile | image and file serializers | None, core API |
| `pas_search` | Products.PlonePAS | `@users`, `@principals` | None, core API |
| `manage-elements`, `manage-content-rules`, `rules-controlpanel`, `+rule`, `plone.ContentRule` | plone.app.contentrules | `@controlpanels/content-rules` | Register conditionally if contentrules becomes a core-addon |
| `iterate_control` | plone.app.iterate (core-addon) | `@workingcopy` | Register conditionally |
| `conversation_view`, `CommentForm`, `EditCommentForm`, `delete-own-comment` | plone.app.discussion (core-addon) | `@comments`, content serializer | Register conditionally |

## Dependency restructuring

**Documentation only (D9):** this section records the dependency edges that block a headless install. Removing them is out of scope of this spec.

Today 9 core packages pull 21 Blicca or core-addon packages into a headless install. A later effort can remove each edge once the package's templates have moved; the removed packages would then become `install_requires` of `plone.classicui` (or of the `Plone` meta package for core-addons).

| Core package | Blicca / core-addon dependencies to remove |
| --- | --- |
| Products.CMFPlone | `plone.app.layout`, `plone.app.theming`, `plonetheme.barceloneta`, `plone.staticresources`, `plone.app.portlets`, `plone.portlets`, `plone.portlet.static`, `plone.portlet.collection`, `plone.app.contentmenu`, `plone.app.viewletmanager`, `plone.app.customerize`, `five.customerize`, `plone.theme`, `plone.outputfilters`, `plone.app.contentrules`, `plone.app.z3cform`, `plone.formwidget.namedfile`, `plone.resource`, `webresource`, `plone.session` |
| plone.restapi | `plone.app.layout` |
| plone.app.contenttypes | `plone.app.layout`, `plone.app.contentmenu`, `plone.portlets`, `plone.app.z3cform` |
| plone.app.dexterity | `plone.app.z3cform`, `plone.formwidget.namedfile`, `plone.portlets`, `plone.contentrules` (interface declarations on `DexterityContent`) |
| plone.app.users | `plone.app.event`, `plone.formwidget.namedfile` |
| plone.app.content | `plone.app.z3cform` |
| plone.app.registry | `plone.app.z3cform` |
| plone.app.relationfield | `plone.app.z3cform` |
| Products.PlonePAS | `plone.session` |

For that later effort: drop a dependency only after its templates and views have moved, and let `plone.classicui` declare every dropped package, so `pip install Plone` keeps installing the same set as today.

The category of `plone.resource`, `webresource`, `plone.session` and `plone.formwidget.namedfile` is a proposal, see open questions.

## PLIP tracking

The PLIP description is the single checklist (D1): one checkbox per package, with one nested checkbox per PR. A package is ticked when all its PRs are merged and released as a new major version (D7).

**Rules for PRs**

- Every PR references the PLIP: `Refs plone/Products.CMFPlone#3953`.
- A move always has two PRs: the source package and `plone.app.layout` `master` (D8). Both link each other and are merged together.
- Widget templates are the exception (D10): their counterpart PR goes to `plone.app.z3cform` instead of `plone.app.layout`.
- The source package PR removes the templates and bumps the major version (D7); it targets Plone 6.3 and later.
- REST API splits get a third PR in `plone.restapi` that switches to the new API.
- All PRs of one package are tested together in one jenkins.plone.org PR job before merging.
- Each PR has a news entry and keeps BBB imports for moved classes.

**Template for the PLIP description**

```markdown
### Core packages: move templates and views
- [ ] Products.CMFPlone
  - [ ] plone/Products.CMFPlone#NNNN Move control panel views (major release)
  - [ ] plone/plone.app.layout#NNNN Add control panel views from CMFPlone
- [x] plone.app.registry
  - [x] plone/plone.app.registry#NNNN …
  - [x] plone/plone.app.layout#NNNN …

### Core packages: REST API split
- [ ] plone.app.querystring
  - [ ] plone/plone.app.querystring#NNNN Keep querybuilderresults, move HTML views
  - [ ] plone/plone.app.layout#NNNN Add query result views
  - [ ] plone/plone.restapi#NNNN Use the new API

### Core-addons (no move)
- plone.app.z3cform, plone.app.event, plone.app.portlets
```

## Acceptance criteria

Every package is tested separately on [jenkins.plone.org](https://jenkins.plone.org): one PR job runs the source package PR and the `plone.app.layout` PR together, plus the `plone.restapi` PR for a REST API split (Jenkins accepts several PR URLs per run). A package is accepted when its job is green and the checks below hold for it.

1. **No templates:** a scan of the source package finds no non-test `.pt` file outside an allowlist (ZMI templates, `plone.distribution` site creation).
2. **No Blicca views:** no `browser:page`, `browser:viewlet`, `browser:viewletManager` or `plone:portlet` registration outside an allowlist of API views (`@@images`, `@@download`, `querybuilderresults`, …).
3. **No regression:** `pip install Plone` installs the same package set as before, and the Blicca test suites (including robot tests) pass.

Checks 1 and 2 can run as a script inside the Jenkins job (proposal: `tools/blicca-separation-check.py` in `buildout.coredev`, based on the scans used for the inventory).

## Open questions

**Resolved**

- [x] `plone_portal_state` and `plone_context_state` stay in `plone.app.layout` for now.
- [x] `plone.app.textfield` keeps its widget templates (too much logic to move).
- [x] `plone.formwidget.namedfile` keeps its templates.
- [x] `plone.app.vocabularies` is core, because `plone.restapi` uses its vocabularies (`@types`, `@vocabularies`); its template is separated.
- [x] *Dependency restructuring* stays as documentation; implementation is out of scope (D9). This includes the `plone.app.layout` dependency of `plone.restapi`.
- [x] Releases: each source package gets a new major version, targeting Plone 6.3 and later (D7).
- [x] `plone.app.dexterity` is not dissolved into `plone.dexterity`: the remaining code is the Plone integration layer with widget bindings to `plone.app.z3cform` (D4) and would create dependency cycles with `plone.namedfile` and `plone.app.relationfield`. See [plone.dexterity and plone.app.dexterity](#plonedexterity-and-ploneappdexterity).
- [x] Acceptance criteria: only the template scan, the view scan and the no-regression check apply. Checks for a headless install, a headless site and the REST API without `plone.app.layout` are dropped (D9).

**Open, re-scoped after D6**

- [ ] Is `plone.app.contentrules` a core-addon in Plone 7 (templates stay), or do its templates move?
- [ ] Is the only template of `plone.session` a Blicca view or a management page (out of scope)?
- [ ] Do the mockup JSON views in `plone.app.content` (`@@getVocabulary`, `fc-*`) move to `plone.app.layout`, or stay as API?
- [ ] Does `plone_redirector_view` move to `plone.app.layout`, or does the redirect logic stay in `plone.app.redirector` as API?
- [ ] Six core packages depend on `plone.app.z3cform` for their forms. Do those forms move completely to `plone.app.layout`?
- [ ] Are the CMFPlone syndication views (RSS, Atom, iTunes, NewsML feeds) Blicca, or output formats that stay in core?
- [ ] Do the Zope root admin views of CMFPlone (`plone-overview`, `plone-addsite`, `plone-upgrade`, …) stay, move, or give way to the `plone.distribution` versions?
- [ ] Are the CMF skin layers in CMFPlone (`skins/`, `skins.xml`) in scope? If yes, the acceptance scans need to cover skin scripts and skin templates too.
