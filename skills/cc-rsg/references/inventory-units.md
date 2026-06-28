# Inventory Units Reference

A catalogue of typical inventory units per language/framework, used during inventory extraction in Phase 2.

This document tells the agent what to enumerate exhaustively from the target codebase. It becomes the basis for the "everything covered" check in Phase 4 inventory-based verification.

<!--
Extension guide:
- Add a language → add a `## {language name}` section.
- Framework-specific (L2) → add a `### {framework name}` subsection inside the relevant language section.
- Trigger threshold: if this file exceeds 800 lines, consider migration to pattern B (split into language / framework two-level structure).
-->

## Table of contents

- [Common concepts](#common-concepts)
- [PHP](#php)
- [COBOL](#cobol)
- [Python](#python)
  - [Flask specifics](#flask-specifics)
  - [FastAPI specifics](#fastapi-specifics)
- [Java](#java)
- [JavaScript / TypeScript](#javascript--typescript)
  - [Next.js specifics (App Router / Pages Router)](#nextjs-specifics-app-router--pages-router)
  - [Expo / React Native specifics](#expo--react-native-specifics)
- [C#](#c)
- [C / C++](#c--c)
- [Dart / Flutter](#dart--flutter)
- [SQL / database schema](#sql--database-schema)
- [When language choice is ambiguous](#when-language-choice-is-ambiguous)
- [Customisation and extension](#customisation-and-extension)
- [Instruction summary for the agent during extraction](#instruction-summary-for-the-agent-during-extraction)

---

## Common concepts

Inventory units exist in 3 tiers:

1. **Macro units**: modules, packages, services
2. **Middle units**: classes, functions, endpoints, jobs
3. **Micro units**: methods, fields, configuration values

The tier you target depends on the granularity preference fixed in Phase 0.

- **High-level overview**: macro units only
- **Medium**: macro + middle
- **Detailed**: all tiers

---

## PHP

### Macro units
- Composer packages (`name` in `composer.json`)
- Namespaces (PSR-4)
- Framework-specific modules (Laravel's `app/Modules/`, Symfony's `src/Bundle/`, etc.)

### Middle units
- Classes (`class`), traits (`trait`), interfaces (`interface`)
- Route definitions (`routes/web.php`, `routes/api.php`, Symfony attribute routes, Slim `app->get`, etc.)
- Artisan commands (Laravel `app/Console/Commands/`)
- Event listeners, jobs, middleware

### Micro units
- Public methods
- Eloquent / Doctrine entity properties
- Configuration-file keys (`config/*.php`)

### Extraction examples
```bash
# Enumerate classes
grep -rEn "^(abstract |final )?class [A-Z]" src/ --include="*.php"

# Enumerate routes (Laravel)
grep -rEn "Route::(get|post|put|patch|delete|any)" routes/ --include="*.php"

# Enumerate Artisan commands
grep -rEn "protected \\\$signature" app/Console/Commands/ --include="*.php"
```

---

## COBOL

### Macro units
- COPYBOOK
- Jobs (JCL steps)

### Middle units
- PROGRAM-ID
- SECTION
- PARAGRAPH
- CALL targets (dynamic and static)

### Micro units
- 01-level items
- File definitions (SELECT / FD)
- DB invocations (EXEC SQL / EXEC CICS)

### Extraction examples
```bash
# Enumerate PROGRAM-ID
grep -rEn "^[ ]*PROGRAM-ID\\." src/ --include="*.cob" --include="*.cbl"

# Enumerate SECTION
grep -rEn "^[ 0-9]+[A-Z0-9-]+ +SECTION\\." src/ --include="*.cob"

# Enumerate CALL statements
grep -rEn "^[ ]*CALL +'" src/ --include="*.cob"
```

### COBOL-specific cautions
- Column position matters (columns 7+ are the effective area; columns 1-6 are sequence numbers).
- The mapping between the logical structure after COPYBOOK expansion and physical files must be recorded separately.
- JCL (Job Control Language) is a separate language from COBOL but is required in the spec because it drives job-trigger conditions.

---

## Python

### Macro units
- Packages (directories that contain `__init__.py`)
- Modules (`.py` files)
- Installable packages (`pyproject.toml` / `setup.py`)

### Middle units
- Classes (`class`)
- Top-level functions (`def`)
- FastAPI / Flask / Django endpoints
- Celery tasks (`@app.task`)
- Click / argparse commands

### Micro units
- Public methods
- Pydantic model / dataclass fields
- Configuration keys (`settings.py`, environment variables)

### Extraction examples
```bash
# Enumerate classes
grep -rEn "^class " --include="*.py" src/

# FastAPI endpoints
grep -rEn "@(app|router)\\.(get|post|put|patch|delete)" --include="*.py"

# Django models
grep -rEn "^class .*\\(.*models\\.Model.*\\):" --include="*.py"
```

### Flask specifics

Flask is a WSGI application defined by Blueprint-based module decomposition and decorator-based route definitions. Per-Blueprint chapter splits work well in the spec.

#### Macro units
- Application-factory function (`def create_app(): ...`)
- Blueprints (per-module feature groupings)
- Flask extensions (Flask-SQLAlchemy, Flask-Login, Flask-Migrate, etc.)

#### Middle units
- View functions (`@app.route` / `@bp.route` / `@app.get`, etc.)
- Class-based views (subclasses of `MethodView`)
- Hooks (`@app.before_request`, `@app.after_request`, `@app.errorhandler`)
- Jinja2 templates (`templates/*.html`)
- Flask-WTF forms (subclasses of `FlaskForm`)
- Flask-SQLAlchemy models (subclasses of `db.Model`)
- CLI commands (`@app.cli.command()` / `@bp.cli.command()`)

#### Micro units
- URL parameters and query parameters per route
- `app.config[...]` configuration keys
- Jinja2 macros and filters

#### Extraction examples
```bash
# Enumerate Blueprints
grep -rEn "Blueprint\\(['\"]" --include="*.py" src/

# Route definitions (app / bp / *_bp)
grep -rEn "@([a-zA-Z_]+)\\.(route|get|post|put|patch|delete)\\(" --include="*.py" src/

# Enumerate hooks
grep -rEn "@([a-zA-Z_]+)\\.(before_request|after_request|teardown_request|errorhandler|context_processor)" --include="*.py" src/

# Jinja2 templates
find templates/ -name "*.html" 2>/dev/null

# CLI commands
grep -rEn "@([a-zA-Z_]+)\\.cli\\.command\\(" --include="*.py" src/
```

#### Flask-specific cautions
- Blueprint names are easy to reuse as chapter IDs in the spec.
- `before_request` / `after_request` often contain hidden business logic — always include them in the chapter.
- In the application-factory pattern, configuration variants (`config.from_envvar`, etc.) should be called out in the operations chapter.

---

### FastAPI specifics

FastAPI is a type-hint-driven ASGI framework. Pydantic schemas and dependency injection (DI) are central concepts; a spec that omits them is incomplete.

#### Macro units
- FastAPI app (`FastAPI()` instances)
- APIRouter (per-feature routers)
- Lifespan (`@asynccontextmanager` / `lifespan` parameter)

#### Middle units
- Endpoints (`@app.get`, `@router.post`, etc., including WebSocket)
- Pydantic schemas (subclasses of `BaseModel`, both request and response)
- Dependencies (functions / classes injected via `Depends(...)`)
- Background tasks (functions invoked via `BackgroundTasks`)
- Middleware (`@app.middleware("http")` / `app.add_middleware(...)`)
- Exception handlers (`@app.exception_handler(...)`)
- Security schemes (`OAuth2PasswordBearer`, `APIKeyHeader`, etc.)

#### Micro units
- Path / query parameter types and constraints (`Query(...)`, `Path(...)`)
- Pydantic field validations (`Field(...)`, `field_validator`)
- Response models (`response_model=...`) and status codes (`status_code=...`)

#### Extraction examples
```bash
# APIRouter definitions
grep -rEn "APIRouter\\(" --include="*.py" src/

# Endpoints (REST + WebSocket)
grep -rEn "@([a-zA-Z_]+)\\.(get|post|put|patch|delete|head|options|websocket)\\(" --include="*.py" src/

# Pydantic schemas
grep -rEn "^class .*\\((BaseModel|RootModel)\\b" --include="*.py" src/

# Dependency functions
grep -rEn "Depends\\(" --include="*.py" src/

# Exception handlers
grep -rEn "@([a-zA-Z_]+)\\.exception_handler\\(" --include="*.py" src/

# Middleware registration
grep -rEn "@([a-zA-Z_]+)\\.middleware\\(|add_middleware\\(" --include="*.py" src/
```

#### FastAPI-specific cautions
- Response Pydantic schemas are the core of the API spec. When the chosen template is `api-service`, always promote them to a dedicated chapter.
- Functions injected via `Depends(...)` often contain crucial logic (authorisation, DB session acquisition, external API client construction, etc.). Consider raising questions in the `architecture_decision` category of the Question Bank.
- OpenAPI schema (`/openapi.json`) is generated automatically — when possible, fetch it at startup and attach to `recon-report.md`.

---

## Java

### Macro units
- Packages (`com.example.foo`)
- Maven modules (`pom.xml`)
- Spring profiles / Bundle / OSGi modules

### Middle units
- Classes (`class`, `interface`, `enum`, `record`)
- Spring `@Controller`, `@Service`, `@Repository`, `@Component`
- Endpoints (`@RequestMapping`, `@GetMapping`, etc.)
- Batch jobs (Spring Batch `Job`, `Step`)
- Scheduled tasks (`@Scheduled`)

### Micro units
- Public methods
- JPA entity fields
- Configuration properties (`application.yml` / `application.properties`)

### Extraction examples
```bash
# Enumerate classes
grep -rEn "^(public |abstract |final )*(class|interface|enum|record) " src/ --include="*.java"

# Spring endpoints
grep -rEn "@(Get|Post|Put|Patch|Delete|Request)Mapping" src/ --include="*.java"

# JPA entities
grep -rEn "@Entity" src/ --include="*.java"
```

---

## JavaScript / TypeScript

### Macro units
- npm packages (`name` in `package.json`)
- Workspaces (monorepo: pnpm workspace, turborepo)
- Frontend: pages, routes (Next.js `app/`, `pages/`)
- Backend: modules (NestJS)

### Middle units
- Exported functions / classes
- React components, Vue components
- Route handlers for Express / Fastify / Hono
- NestJS Controller / Service / Module
- Background jobs (BullMQ, Agenda)

### Micro units
- Public methods
- Zod / Yup / TypeScript type definitions
- Environment variables

### Extraction examples
```bash
# Exported functions / classes
grep -rEn "^export (default )?(async )?(function|class|const)" --include="*.ts" --include="*.tsx" --include="*.js" src/

# Express routes
grep -rEn "(app|router)\\.(get|post|put|patch|delete)\\(" --include="*.ts" --include="*.js" src/

# React components (function components)
grep -rEn "^export (default )?function [A-Z]" --include="*.tsx" --include="*.jsx" src/
```

### Next.js specifics (App Router / Pages Router)

Next.js is a convention-over-configuration framework: file names themselves become inventory units. App Router (13+) and Pages Router have different structures — keep them separate.

#### Macro units
- `app/` directory (App Router projects)
- `pages/` directory (Pages Router projects; `pages/api/` is API endpoints)
- Route Group (directories of the form `(group_name)` — logical groupings that do not appear in the URL)
- Parallel Routes (`@slot_name`), Intercepting Routes (`(.)`, `(..)`, `(...)`)

#### Middle units (App Router)
- Pages (`app/**/page.tsx` / `page.ts`)
- Layouts (`app/**/layout.tsx`)
- Loading UI (`app/**/loading.tsx`)
- Error boundaries (`app/**/error.tsx` / `global-error.tsx`)
- Not Found (`app/**/not-found.tsx`)
- API routes (`app/**/route.ts` — Route Handler)
- Server Actions (files / functions that include `'use server'`)
- Server Component / Client Component boundary (`'use client'` directive)
- Middleware (`middleware.ts` at the project root)
- Instrumentation (`instrumentation.ts`)

#### Middle units (Pages Router)
- Pages (`pages/**/*.tsx`)
- API endpoints (`pages/api/**/*.ts`)
- Special files: `_app.tsx`, `_document.tsx`, `_error.tsx`
- Pages containing `getStaticProps` / `getStaticPaths` / `getServerSideProps`

#### Micro units
- Dynamic route segments (`[id]`, `[...slug]`, `[[...slug]]`)
- Route metadata (`generateMetadata`, `metadata` exports)
- Config files (`next.config.js` / `next.config.mjs`)
- Environment variables (those starting with `NEXT_PUBLIC_` are exposed to the client)

#### Extraction examples
```bash
# App Router pages
find app -name "page.tsx" -o -name "page.ts" -o -name "page.jsx" -o -name "page.js" 2>/dev/null

# App Router API routes
find app -name "route.ts" -o -name "route.js" 2>/dev/null

# Pages Router pages (excluding _ files)
find pages -name "*.tsx" -o -name "*.ts" 2>/dev/null | grep -vE "/(_app|_document|_error)\\."

# Pages Router API
find pages/api -type f 2>/dev/null

# Files containing a Server Action
grep -rEn "^[\"']use server[\"']" --include="*.ts" --include="*.tsx" .

# Client Component declarations
grep -rEn "^[\"']use client[\"']" --include="*.ts" --include="*.tsx" app/

# Middleware
ls middleware.ts middleware.js 2>/dev/null
```

#### Next.js-specific cautions
- **Mixed App Router and Pages Router** is common in real projects. When both are detected, split chapters in the spec.
- Server Actions look like ordinary functions in source but cross the network boundary. **Enumerate them as API endpoints.**
- The presence/absence of `'use client'` changes the execution environment. Reference it in the security / performance chapters.
- The `experimental` section of `next.config.js` is a strong basis for future instability — always state it in the spec.

---

### Expo / React Native specifics

Expo / React Native targets **mobile apps**. Different units (screens, navigation, native modules, build config) dominate compared to a web app. Choose a future `mobile-app.md` template (or a mobile customisation of `web-app.md`) instead of using `web-app.md` directly.

#### Macro units
- App entry (`App.tsx` / `app/_layout.tsx` for Expo Router)
- Navigator hierarchy (nested Stack / Tab / Drawer)
- Platform directories (`android/`, `ios/` in the Bare Workflow)

#### Middle units
- Screens
  - `screens/*.tsx` / `screens/**/*Screen.tsx` (traditional structure)
  - `app/**/*.tsx` (Expo Router; similar to Next.js App Router)
- Navigator definitions (`createNativeStackNavigator`, `createBottomTabNavigator`, `createDrawerNavigator`)
- Custom hooks (`hooks/use*.ts`)
- Native module references (`NativeModules.XXX`, Expo Modules such as `expo-camera`)
- Background tasks (`expo-background-fetch`, `expo-task-manager`)
- Storage / persistence (`AsyncStorage`, `SecureStore`, MMKV, Realm)

#### Micro units
- Screen navigation parameter types (`RootStackParamList`)
- Permission declarations (`permissions` / `infoPlist` / `androidManifest` in `app.json`)
- Environment variables (`EXPO_PUBLIC_*`, `Constants.expoConfig`)

#### Build / distribution configuration
- `app.json` / `app.config.ts` / `app.config.js` (app metadata, build configuration)
- `eas.json` (EAS Build / Submit configuration; development / preview / production profiles)
- `package.json` `scripts` (`expo start`, `expo run:ios`, `expo prebuild`, etc.)
- `metro.config.js` (bundler configuration)
- `babel.config.js` (plugin composition, especially `react-native-reanimated/plugin`, etc.)

#### Extraction examples
```bash
# Screen files (traditional structure)
find . -path ./node_modules -prune -o -name "*Screen.tsx" -print 2>/dev/null

# Expo Router screens (under app/)
find app -name "*.tsx" -not -name "_*" 2>/dev/null

# Navigator creation
grep -rEn "create(NativeStack|BottomTab|Drawer|Material(Top|Bottom)Tab)Navigator" --include="*.tsx" --include="*.ts" .

# Expo Module usage
grep -rEn "from ['\"]expo-[a-z-]+['\"]" --include="*.ts" --include="*.tsx" .

# Permission declarations (app.json / app.config.*)
grep -nE "(permissions|infoPlist|androidManifest)" app.json app.config.* 2>/dev/null

# EAS build profiles
cat eas.json 2>/dev/null | grep -E '"(development|preview|production)"'
```

#### Expo / React Native-specific cautions
- **Decide Managed vs Bare Workflow first** (presence of `android/` `ios/` directories, or traces of `expo prebuild`). The spec structure changes significantly.
- Native modules (`expo-camera`, `expo-location`, etc.) require **OS-specific permissions**. Always cover them in the security / operations chapters.
- `runtimeVersion` in `app.json` and `channel` in `eas.json` decide **OTA (Over-the-Air) update** behaviour. Mention this in the versioning chapter.
- **Behaviour differences between iOS and Android** (push notifications, background execution, file access) should be split into explicit chapters or sections.
- Check whether `react-native-web` output is configured (if yes, also add a web-app chapter).

---

## C#

### Macro units
- Assemblies (`.csproj`)
- Namespaces (`namespace`)
- Solutions (`.sln`)

### Middle units
- Classes (`class`, `interface`, `record`, `struct`)
- ASP.NET Core Controller / Minimal API endpoints
- Hosted services (`IHostedService`)
- Background workers

### Micro units
- Public methods
- EF Core entity properties
- Configuration keys in `appsettings.json`

### Extraction examples
```bash
# Enumerate classes
grep -rEn "^[[:space:]]*(public |internal )?(abstract |sealed )?(class|interface|record|struct) " src/ --include="*.cs"

# ASP.NET endpoints
grep -rEn "\\[Http(Get|Post|Put|Patch|Delete)\\]" src/ --include="*.cs"
```

---

## C / C++

C/C++ targets range from **CLIs and system daemons** to **embedded firmware**,
**libraries/SDKs**, and **desktop apps**. The `source-map.py` C/C++ extractor
emits `cpp_class` / `cpp_struct` / `cpp_union` / `cpp_enum` / `cpp_namespace` /
`cpp_function` units (a single `cpp_` prefix covers both C and C++); group them
into the inventory below. Header files with only prototypes fall back to a
coarse `source_file` unit.

### Macro units
- Build targets / modules (`CMakeLists.txt` targets, `Makefile` rules, `add_library` / `add_executable`)
- Namespaces (`namespace`, C++ only) and top-level library headers
- The package / component itself (a directory of related `.c`/`.cpp` + headers)
- Program entry (`int main(...)`)

### Middle units
- Classes (`class X`, often with a base list `: public Base`)
- Structs / unions (`struct`, `union` — the dominant aggregate in C)
- Enums (`enum`, `enum class` / `enum struct`)
- Free functions and out-of-line member definitions (`ReturnType Class::method(...)`)
- Templates (`template<...> class/struct/function`) — treat as the declared entity
- Public API surface exported from headers

### Micro units
- Public methods on classes
- Struct / union fields
- Macros (`#define`), compile-time config (`#ifdef`, build flags)
- Global constants and `extern` declarations

### Dependencies
- Build system (`CMakeLists.txt`, `Makefile`, `meson.build`, Bazel)
- `#include` graph (system vs. project headers)
- Linked libraries (`target_link_libraries`, `-l` flags) and package managers (Conan, vcpkg)

### Extraction examples
```bash
# Classes / structs / unions / enums / namespaces
grep -rEn "^[[:space:]]*(typedef[[:space:]]+)?(class|struct|union|enum|namespace)[[:space:]]" \
  src/ --include="*.c" --include="*.cc" --include="*.cpp" --include="*.h" --include="*.hpp"

# Top-level / out-of-line function definitions (signature followed by `{`, no trailing `;`)
grep -rEn "^[A-Za-z_].*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\\([^;]*$" src/ --include="*.cpp"

# Macros and conditional compilation
grep -rEn "^[[:space:]]*#[[:space:]]*(define|ifdef|ifndef|if)" src/ --include="*.h"

# Build targets
grep -rEn "add_(library|executable)\\(" . --include=CMakeLists.txt
```

### C/C++-specific cautions
- Regex extraction is conservative (the project does not use tree-sitter). Known gaps:
  - Anonymous structs named via `typedef struct {…} Name;` are not captured by name
    (the `struct Name {…}` form is). Add such units manually if they are load-bearing.
  - Function signatures spanning multiple lines (return type / args wrapped) may be missed.
  - Macro-generated declarations and heavy template metaprogramming are out of scope.
- `.h` is ambiguous (C or C++); both are handled by the same `cpp_*` kinds. A header
  with only prototypes/forward declarations is recorded as one `source_file` unit so
  MECE coverage is preserved — inventory the **defining** translation unit.
- Separate the public API (headers) from the implementation (`.c`/`.cpp`) when the
  spec distinguishes interface from internals.

### High-fidelity extraction (optional)

When a compilation database is available, `source-map.py` can parse C/C++ with
**libclang** instead of regexes, which removes every "known gap" above (macros
are expanded, templates and multi-line signatures resolve, out-of-line members
and qualified names are exact, and `struct`-returning functions are never
mistaken for type definitions). It also recovers methods of non-template
classes as `cpp_function` units.

Enable it:
1. Generate the database — e.g. CMake (+ Ninja): configure with
   `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON`, producing `build/compile_commands.json`.
   (Other build systems: Bear `bear -- make`, or `compiledb`.)
2. `pip install libclang` (bundles the native library; no separate LLVM needed).
3. Run with `--compile-commands <build dir or compile_commands.json>` (the file
   is also auto-discovered in `build/`, `out/`, `cmake-build-*`, and one level
   below those — e.g. multi-config layouts like `build/msvc_release/`; a direct
   `build/compile_commands.json` wins, ties go to the most recent build).

The output schema is **identical** to the regex tier (same `cpp_*` kinds, line
ranges, fingerprints), so the MECE / coverage / traceability chain is unchanged;
`stats.cpp_extractor` reports `clang` / `regex` / `mixed`. When a high-fidelity
run was possible but did not happen, the fallback is **not silent**: the
extractor sets `stats.cpp_degraded_reason` (`libclang_missing` / `db_missing` /
`libclang_and_db_missing` / `clang_failed`) and prints a stderr warning, and
Phase 2 reads this signal to prompt the user to remediate (install libclang /
generate the database → re-run). The zero-dependency, no-build regex path still
works and remains available (this is a fidelity choice, not a correctness gate —
it never blocks continuing). Only files present in the database use libclang;
C/C++ files outside it still use regex. Remaining libclang-tier limitations:
free **function templates** and members of **class templates** are not exposed
as definitions by libclang and are skipped (the class template itself is still
captured).

---

## Dart / Flutter

Flutter targets **desktop and mobile GUI apps** (and web). The dominant units
are widgets, screens, state-management objects, and local persistence. The
`source-map.py` Dart extractor emits `dart_class` / `dart_mixin` / `dart_enum`
/ `dart_extension` / `dart_function` units; group them into the inventory below.

### Macro units
- Feature directories (`lib/features/<feature>/`, `lib/src/<feature>/`)
- The package itself (`name` in `pubspec.yaml`)
- App entry (`lib/main.dart`, `runApp(...)`)
- Flavors / entry points (`main_dev.dart`, `main_prod.dart`)

### Middle units
- Widgets (`class X extends StatelessWidget` / `StatefulWidget`, and the paired `State<X>`)
- Screens / pages (`*Screen`, `*Page`, or files under a `screens/` / `pages/` directory)
- State management:
  - Provider / Riverpod (`ChangeNotifier`, `Notifier`, `*Provider`, `Consumer`)
  - Bloc / Cubit (`extends Bloc<Event, State>` / `extends Cubit<State>`)
  - GetX (`GetxController`), MobX (`Store`)
- Repositories / services / data sources (`*Repository`, `*Service`, `*DataSource`)
- Models / entities (`class`, often with `fromJson` / `toJson`, `freezed`, `json_serializable`)
- Routing (go_router `GoRoute`, `Navigator` routes, `onGenerateRoute`)
- Enums, mixins, extensions

### Micro units
- Public methods on controllers / repositories
- Model fields
- Local DB schema (`sqflite` `CREATE TABLE`, Drift tables, Isar/Hive type adapters)
- Build/runtime config (`--dart-define`, `String.fromEnvironment`, `flutter_dotenv`)

### Dependencies
- `pubspec.yaml` `dependencies` / `dev_dependencies`
- Platform channels (`MethodChannel`, `EventChannel`) and native plugins
- Generated code markers (`*.g.dart`, `*.freezed.dart`) — treat as derived, not primary

### Extraction examples
```bash
# Widgets / classes / mixins / enums / extensions
grep -rEn "^(abstract |final |sealed |base |mixin |interface )*(class|mixin|enum|extension) " lib/ --include="*.dart"

# Widget subclasses specifically
grep -rEn "extends (StatelessWidget|StatefulWidget|State<)" lib/ --include="*.dart"

# State management
grep -rEn "extends (ChangeNotifier|Bloc<|Cubit<|GetxController|StateNotifier<)|class .*Notifier" lib/ --include="*.dart"

# Routes (go_router)
grep -rEn "GoRoute\(|GoRouter\(" lib/ --include="*.dart"

# Local DB schema
grep -rEn "CREATE TABLE|Database\.|openDatabase\(" lib/ --include="*.dart"

# Dependencies
sed -n '/^dependencies:/,/^[a-z]/p' pubspec.yaml
```

### Flutter-specific cautions
- A `StatefulWidget` and its `State<...>` are one logical unit — keep them in
  one INV (or two tightly linked INVs), not scattered.
- Generated files (`*.g.dart`, `*.freezed.dart`) are derived from annotations.
  Inventory the **source** declaration, and exclude the generated file via
  `exclusions.yaml` so MECE is not inflated.
- State-management choice (Provider / Riverpod / Bloc / GetX) decides the data
  flow chapter — identify it during recon and state it explicitly.
- Platform differences (desktop window management, mobile permissions, file
  access) belong in the build/distribution and operations chapters.

---

## SQL / database schema

Database schemas are part of the spec target alongside the source code itself.

### Inventory units
- Tables
- Views
- Stored procedures / functions
- Triggers
- Indexes
- Foreign-key constraints

### Extraction methods
- Parse migration files (Rails, Laravel, Django, Flyway, Liquibase)
- Read `information_schema` from a production DB (when possible)
- Read ER diagrams / DDL files directly

---

## When language choice is ambiguous

### Multi-language repository
- Produce a separate inventory per language and tag each entry with the language.
- Example: add `"language": "php"` to each entry in `inventory.json`.

### DSL / configuration files are essential
- For projects centred on a DSL — Terraform `.tf`, Kubernetes `.yaml`, Ansible playbooks — treat those DSLs as middle units.
- Resource definitions (`resource "aws_instance" ...`), Pods / Services / Deployments, and playbook tasks become the units.

### Microservices
- Treat each service as a macro unit, and develop the per-language inventory inside each service as middle units and below.

---

## Customisation and extension

When the user wants to add inventory units for a new language / framework, append to this file. The v1 release does not provide a UI-based addition mechanism.

A future version may split this into `references/inventory-units-{custom}.md`-style files.

---

## Instruction summary for the agent during extraction

1. **First, run `scripts/source-map.py --target <root>`**. This auto-extracts source units (SRC-NNNN) and saves them to `.cc-rsg/source-map.json`. It understands Ruby, Python, JavaScript/TypeScript, Dart, and C/C++ in detail, and records every other recognised source file (Swift, Kotlin, Rust, Go, etc.) as a coarse file-level unit — so the MECE chain works on any stack.
2. Identify the target codebase's primary language(s) from `recon-report.md`.
3. Consult the matching section and plan an extraction strategy.
4. **Group `source-map.json` units into conceptual units**. Many-to-one (multiple SRC → 1 INV) is acceptable, subject to the granularity rules below.
5. Save the result to `inventory.json`. The canonical schema is in `references/phase-2-plan.md` (an object with a `units` array; fields `type`, `covered_by`). Optionally record the corresponding SRC-NNNN in `related_source_ids` as provenance — but note the MECE check does **not** read it. Phase 4 verification matches the `[REF: path:Lx-Ly]` markers you write in chapters against `source-map.json` (see `scripts/build-trace.py`).
6. Tag commented-out / deprecated / test code that you encounter (e.g. `"deprecated": true`).

### Fallback when source-map.py reports 0 units

`source-map.py` already records recognised source files as file-level units, so
a `files_scanned = 0` result means the stack uses extensions outside the
recognised set. In that case, hand-generate a file-level `source-map.json`
(one unit per source file, `kind: "file"`, `line_range: [1, N]`) before running
`build-trace.py`, so the MECE coverage check still has a population to verify.

---

## Granularity rules (mandatory)

### Minimum count

```
inventory.json minimum count = max(50, files_scanned // 20)
```

- Example: 1,000-file Rails project → at least 50 entries
- Example: 5,000-file large JS project → at least 250 entries

`scripts/coverage-check.py` fails on this rule. The value is **derived automatically from `source-map.json`'s `stats.files_scanned`**.

### Macro-unit prohibition

❌ **Grouping-style INVs like the following are forbidden**:
- `controller_group` "Account-family controllers" ← bundling Account, Sessions, Twofa together
- `model_group` "User-family models" ← bundling User, Group, Member together
- `module_group` "Wiki/Document family" ← bundling multiple independent responsibilities

These are too coarse: maintainers cannot tell which file to modify.

✅ **Correct granularity**:
- 1 controller class = 1 INV
- 1 model class = 1 INV
- 1 service class = 1 INV
- 1 job class = 1 INV
- 1 concern module = 1 INV
- 1 mailer class = 1 INV
- For large controllers (300+ lines), **per-action additional INVs are allowed**

`scripts/coverage-check.py` treats an INV as "macro type" when its `type` ends
with a grouping suffix (`_group` / `_bundle` / `_category` / `_section`) or one
of its tokens is a bare grouping word (`group` / `bundle` / `category`), and
**fails if such INVs exceed 20% of all INVs**. Legitimate layer names such as
`domain`, `module`, or `service` are **not** treated as macro.

---

## Ruby on Rails catalogue (detailed)

For Rails applications, always extract by the following units. **An `inventory.json` that does not satisfy this catalogue is considered non-compliant.**

### 1. Controllers (`app/controllers/**/*.rb`)
- Every file ending in `_controller.rb` × 1 INV
- type: `controller`
- name: class name (e.g. `IssuesController`)
- file: the file
- Large controllers (300+ lines) may also add **per-action INVs** (type: `controller_action`)

### 2. Models (`app/models/**/*.rb`)
- Every model class × 1 INV (including direct ApplicationRecord descendants and indirect descendants like Principal/User)
- type: `model` / `model_subclass`
- name: class name (e.g. `Issue`, `Project`)

### 3. Concerns (`app/controllers/concerns/`, `app/models/concerns/`)
- 1 module = 1 INV
- type: `concern`

### 4. Services / use cases (`app/services/`, `app/use_cases/`, `lib/services/`)
- 1 class = 1 INV
- type: `service`

### 5. Jobs (`app/jobs/**/*.rb`)
- 1 class = 1 INV
- type: `job`

### 6. Mailers (`app/mailers/**/*.rb`)
- 1 class = 1 INV
- type: `mailer`

### 7. Helpers (`app/helpers/**/*.rb`)
- 1 module = 1 INV
- type: `helper`

### 8. Lib (`lib/**/*.rb`)
- 1 class or 1 module = 1 INV
- type: `lib_class` / `lib_module`

### 9. Migrations (`db/migrate/**/*.rb`)
- 1 migration file = 1 INV (treated per table)
- type: `migration`
- name: migration class name (e.g. `CreateIssues`)

### 10. Route groups (`config/routes.rb`)
- One `resources :foo do … end` block × 1 INV
- One `namespace :api do … end` block × 1 INV
- type: `rails_route`
- name: prefixed name like `resources:issues` / `namespace:api/v1`

### 11. View groups (`app/views/**`)
- Group per resource (e.g. `app/views/issues/`) × 1 INV
- type: `view_group`
- name: directory name

### 12. JavaScript modules (`app/javascript/**`)
- 1 export = 1 INV (per file if file count is small)
- type: `js_export`

### 13. Configuration files (`config/*.yml`, `config/initializers/**/*.rb`)
- Key initializers: 1 file = 1 INV
- type: `config`

### 14. Mailer templates (`app/views/mailer/**/*.erb`)
- 1 file = 1 INV
- type: `mailer_view`

### Rails granularity guideline

| Rails app size | Minimum INV | Approximate breakdown |
|----------------|---------|---------|
| Small (100 .rb) | 50 | controllers 10, models 15, jobs 3, lib 5, migrations 10, routes 5, views 2 |
| Medium (500 .rb) | 50 | controllers 30, models 50, services 20, jobs 10, migrations 30, routes 15, helpers 10 |
| Large (1,000+ .rb) | 90+ | controllers 80, models 80, concerns 20, services 30, jobs 20, migrations 100+, routes 30 |

Example: a medium Rails codebase with ~1,000 .rb files → at least ~90 INVs are required (an agent that stops at 30 is under-granular).
