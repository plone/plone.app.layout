# Blicca separation: overview

140 Blicca templates and 184 registered view classes in 14 core packages move to `plone.app.layout`.
Core-addons keep theirs.
Part of [PLIP #3953](https://github.com/plone/Products.CMFPlone/issues/3953); the rules are in [blicca-separation-spec.md](blicca-separation-spec.md).

As of 2026-09-26, measured in `buildout.coredev` 6.3 (`Products.CMFPlone` from `master`).

## Where the templates and views go

```mermaid
flowchart LR
    subgraph core ["Core packages (14 with work)"]
        direction TB
        CMFPlone["Products.CMFPlone<br/>72 templates · 90 views"]
        content["plone.app.content<br/>15 · 35"]
        contenttypes["plone.app.contenttypes<br/>14 · 8"]
        dexterity["plone.app.dexterity<br/>10 · 13"]
        users["plone.app.users<br/>8 · 11"]
        rest["8 more packages<br/>19 · 27"]
        schema["plone.schema<br/>2 · 0"]
    end
    layout[["plone.app.layout<br/>master, 7.0 alpha<br/>today 49 · 47"]]
    subgraph addons ["Core-addons: templates stay"]
        direction TB
        z3cform["plone.app.z3cform<br/>29 · 4"]
        event["plone.app.event<br/>7 · 13"]
        portlets["plone.app.portlets<br/>20 · 23"]
    end
    CMFPlone --> layout
    content --> layout
    contenttypes --> layout
    dexterity --> layout
    users --> layout
    rest --> layout
    schema -. "widget templates" .-> z3cform
```

## Templates and view classes per package

| Package | Category | Blicca templates | View classes | Destination |
| --- | --- | ---: | ---: | --- |
| Products.CMFPlone | Core | 72 | 90 | plone.app.layout |
| plone.app.content | Core | 15 | 35 | plone.app.layout |
| plone.app.contenttypes | Core | 14 | 8 | plone.app.layout |
| plone.app.dexterity | Core | 10 | 13 | plone.app.layout |
| plone.app.users | Core | 8 | 11 | plone.app.layout |
| Products.CMFEditions | Core | 6 | 8 | plone.app.layout |
| plone.dexterity | Core | 4 | 3 | plone.app.layout |
| plone.schemaeditor | Core (split) | 3 | 7 | plone.app.layout, API stays |
| plone.batching | Core (split) | 3 | 2 | plone.app.layout, `Batch` stays |
| plone.schema | Core | 2 | 0 | plone.app.z3cform |
| plone.app.querystring | Core (split) | 1 | 3 | plone.app.layout, API stays |
| plone.protect | Core | 1 | 2 | plone.app.layout |
| plone.app.vocabularies | Core (split) | 1 | 0 | plone.app.layout, vocabularies stay |
| plone.app.versioningbehavior | Core | 0 | 2 | plone.app.layout |
| **Total to move** | | **140** | **184** | |
| plone.locking, plone.app.contentlisting, plone.app.workflow, plone.app.linkintegrity, plone.app.redirector | Core (check) | 0 | 8 | check whether API |
| plone.app.textfield | Core (keep) | 3 | 1 | stays |
| plone.formwidget.namedfile | Core (keep) | 4 | 1 | stays |
| plone.app.z3cform | Core-addon | 29 | 4 | stays |
| plone.app.event | Core-addon | 7 | 13 | stays |
| plone.app.portlets | Core-addon | 20 | 23 | stays |
| plone.app.contentrules | open | 3 | 39 | open question |
| plone.app.layout | Blicca (target) | 49 | 47 | receives the moves |

```mermaid
xychart-beta horizontal
    title "Blicca templates to move"
    x-axis ["CMFPlone", "p.a.content", "p.a.contenttypes", "p.a.dexterity", "p.a.users", "CMFEditions", "plone.dexterity", "schemaeditor", "batching", "plone.schema", "p.a.querystring", "plone.protect", "p.a.vocabularies"]
    y-axis "Templates" 0 --> 80
    bar [72, 15, 14, 10, 8, 6, 4, 3, 3, 2, 1, 1, 1]
```

```mermaid
xychart-beta horizontal
    title "Registered view classes to move"
    x-axis ["CMFPlone", "p.a.content", "p.a.dexterity", "p.a.users", "p.a.contenttypes", "CMFEditions", "schemaeditor", "plone.dexterity", "p.a.querystring", "batching", "plone.protect", "versioningbehavior"]
    y-axis "View classes" 0 --> 100
    bar [90, 35, 13, 11, 8, 8, 7, 3, 3, 2, 2, 2]
```

## Dependency graph today

Every solid arrow is a core package that pulls a Blicca or core-addon package into a headless install (21 packages over 9 core packages).

```mermaid
flowchart LR
    Plone --> classicui[plone.classicui]
    Plone --> restapi
    classicui --> distribution[plone.distribution]
    classicui --> layout
    distribution --> CMFPlone
    distribution --> restapi

    subgraph core [Core]
        CMFPlone[Products.CMFPlone]
        restapi[plone.restapi]
        contenttypes[plone.app.contenttypes]
        dexterity[plone.app.dexterity]
        users[plone.app.users]
        content[plone.app.content]
        registry[plone.app.registry]
        relationfield[plone.app.relationfield]
        plonepas[Products.PlonePAS]
    end

    subgraph blicca [Blicca]
        layout[plone.app.layout]
        theming["theming: plone.app.theming, plonetheme.barceloneta,<br/>plone.staticresources, plone.resource, webresource"]
        ui["UI: plone.app.contentmenu, plone.app.viewletmanager,<br/>plone.app.customerize, five.customerize,<br/>plone.theme, plone.outputfilters"]
    end

    subgraph addons [Core-addons]
        z3cform[plone.app.z3cform]
        event[plone.app.event]
        portlets["plone.app.portlets, plone.portlets,<br/>plone.portlet.static, plone.portlet.collection"]
        rules["plone.app.contentrules (open)"]
    end

    undecided["open: plone.session,<br/>plone.formwidget.namedfile"]

    CMFPlone --> layout & theming & ui & z3cform & portlets & rules & undecided
    restapi --> layout
    contenttypes --> layout & ui & portlets & z3cform
    dexterity --> z3cform & portlets & undecided
    users --> event & undecided
    content --> z3cform
    registry --> z3cform
    relationfield --> z3cform
    plonepas --> undecided
```

## Dependency graph after a later restructuring

Documentation only: implementing this is out of scope of the PLIP (D9).
The headless install (`plone.distribution`, `Products.CMFPlone`, `plone.restapi`) no longer reaches Blicca packages, except through the state views that stay in `plone.app.layout` for now (dashed).

```mermaid
flowchart LR
    Plone --> classicui[plone.classicui]
    Plone --> restapi
    Plone --> addons

    subgraph headless ["Headless install"]
        distribution[plone.distribution]
        CMFPlone[Products.CMFPlone]
        restapi[plone.restapi]
        corepkgs["core packages:<br/>plone.app.content, plone.app.contenttypes,<br/>plone.app.dexterity, plone.app.users, …"]
    end

    subgraph blicca [Blicca]
        layout[plone.app.layout]
        theming[theming stack]
        ui[UI packages]
    end

    addons["core-addons:<br/>plone.app.z3cform, plone.app.event,<br/>plone.app.portlets"]

    classicui --> distribution
    classicui --> layout & theming & ui
    distribution --> CMFPlone & restapi
    restapi --> CMFPlone
    CMFPlone --> corepkgs
    layout --> CMFPlone
    addons --> layout
    restapi -. "state views, stay for now" .-> layout
```

## How the numbers were produced

- **Blicca templates:** non-test `.pt` files in the installed package, minus ZMI templates (paths containing `zmi`, `manage` or `www/`).
- **View classes:** unique `class` (or portlet `renderer`) values of `browser:page`, `browser:view`, `browser:viewlet`, `browser:viewletManager` and `plone:portlet` registrations in non-test ZCML.
- **Dependencies:** `install_requires` closure of `Products.CMFPlone`, `plone.distribution` and `plone.restapi`, stopping at the first Blicca or core-addon package.
- Unreleased PR branches are not included.
