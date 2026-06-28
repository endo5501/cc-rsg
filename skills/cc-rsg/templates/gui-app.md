---
template_name: gui-app
template_version: 0.1.0
last_updated: 2026-06-28
description: Desktop / mobile GUI application spec template. For client apps the user operates through native screens (Flutter, Electron, native iOS/Android, desktop GUI).
---

# Desktop / mobile GUI application spec template

This template defines the chapter outline for the spec of a client-side GUI
application that the user operates through screens — as opposed to a
server-rendered web app (see `templates/web-app.md`).

Designed for: Flutter (desktop / mobile / web), React Native / Expo, Electron /
Tauri, native iOS (Swift/SwiftUI), native Android (Kotlin/Compose), and other
desktop GUI toolkits (Qt, WPF, Avalonia). The defining traits are local state
management, a screen/navigation graph, on-device persistence, and a
platform-specific build/distribution pipeline.

---

## Chapter outline

### Chapter 1: Overview

<!-- meta: bird's-eye view of the whole app. A 3-minute "what is this" for the reader. -->

#### 1.1 Application purpose
- The problem this app solves
- Primary users and supported platforms (desktop / mobile / web)
- Distribution channel (store, sideload, internal)

#### 1.2 Main use cases
- 3 to 5 representative user journeys

#### 1.3 High-level architecture diagram
- App, state layer, data layer, OS/native boundaries
- Mermaid notation when appropriate

---

### Chapter 2: Architecture overview

<!-- meta: design decisions and overall structure. Capture WHY this shape. -->

#### 2.1 Framework / toolkit and major libraries
- Language, UI toolkit, and key packages with versions
- For Flutter: `pubspec.yaml` dependencies of note

#### 2.2 Architecture pattern
- Layered / Clean / MVVM / feature-first, etc.
- State-management approach (Provider, Riverpod, Bloc/Cubit, Redux, MobX, GetX)
- Reason for adoption (to the extent it can be inferred)

#### 2.3 Directory structure
- Responsibility of each major directory (`lib/features/`, `lib/core/`, etc.)
- Naming and placement conventions

#### 2.4 Dependencies and boundaries
- External services / APIs
- Native platform channels and plugins
- Local stores (DB, key-value, secure storage)

---

### Chapter 3: Screens and navigation

<!-- meta: UI structure from the user's perspective. -->

#### 3.1 Screen list
| Screen ID | Screen name | Route | Entry condition | Primary state |
|---|---|---|---|---|
| SC-001 | Splash | / | app launch | - |
| SC-002 | Library | /library | after init | LibraryController |
| ... | ... | ... | ... | ... |

#### 3.2 Navigation graph
- Major navigation paths (Mermaid)
- Modal / dialog / deep-link entry points
- Back-stack and exit behaviour

#### 3.3 Details of each screen
For each screen:
- Displayed widgets / components
- Inputs and their validation
- Actions (what each control triggers)
- Display conditions (state, platform, permission)

---

### Chapter 4: Features and behaviour

<!-- meta: full list of user-facing capabilities. The pillar of inventory-based verification. -->

#### 4.1 Feature catalogue
| Feature ID | Feature | Entry screen | Controller / handler | Summary |
|---|---|---|---|---|
| FT-001 | Import file | Library | ImportController | Pick + parse a file |
| ... | ... | ... | ... | ... |

#### 4.2 Per-feature flow
- Trigger → state change → side effects → result
- Error / empty / loading states
- Platform differences in behaviour

---

### Chapter 5: State management and data flow

<!-- meta: how state lives and moves. The core of a client app's correctness. -->

#### 5.1 State containers
- Controllers / notifiers / blocs / stores and what each owns
- Scope (global, per-screen, ephemeral)

#### 5.2 Data flow
- View → action → state → view loop (Mermaid sequence)
- Async handling (futures, streams, isolates/workers)

#### 5.3 Persistence of state
- What is restored across launches
- Migration of stored state across versions

---

### Chapter 6: Data model and local persistence

<!-- meta: structure and semantics of on-device data. -->

#### 6.1 Entity list
Per entity:
- Class name and source file
- Field list (type, nullability, business meaning)
- Serialization (`fromJson`/`toJson`, freezed, codable)

#### 6.2 Local schema
- Store technology (sqflite / Drift / Isar / Hive / Realm / Core Data / Room)
- Tables / boxes / collections and their columns
- Indexes and relations
- ER diagram (Mermaid)

#### 6.3 Schema/version migrations
- Migration steps between schema versions
- Behaviour on downgrade or corrupt store

---

### Chapter 7: External integration

<!-- meta: boundaries and failure propagation. -->

#### 7.1 Integration partners
| Partner | Protocol | Purpose | Behaviour on failure |
|---|---|---|---|
| Sync API | HTTPS REST | Cloud sync | Queue + retry; offline mode |
| ... | ... | ... | ... |

#### 7.2 Native / OS integration
- Platform channels, plugins, permissions (camera, location, files, notifications)
- File-system and OS-level interactions (desktop window, tray, deep links)

#### 7.3 Details per integration
- Authentication, request/response example
- Timeout / retry / offline behaviour
- Idempotency and conflict resolution

---

### Chapter 8: Build and distribution

<!-- meta: how the app is built, signed, and shipped per platform. -->

#### 8.1 Build configuration
- Build flavors / schemes / environments
- Config injection (`--dart-define`, env files, build args)

#### 8.2 Per-platform packaging
| Platform | Artifact | Signing | Channel |
|---|---|---|---|
| Windows | MSIX / exe | code-sign cert | internal |
| macOS | dmg / pkg | notarization | - |
| Android | apk / aab | keystore | Play |
| iOS | ipa | provisioning | App Store |

#### 8.3 Release procedure
- Build command(s)
- Versioning (`pubspec.yaml` version+build, semantic versioning)
- Update mechanism (store, OTA, auto-update)
- Rollback procedure

#### 8.4 Diagnostics
- Crash reporting / analytics
- Local log location and retention

---

### Chapter 9: Known constraints and unresolved items

<!-- meta: spec credibility safeguard. -->

#### 9.1 Known technical constraints
- Platform-specific limits, performance ceilings
- Known bugs / workarounds

#### 9.2 Unresolved items
- Place the `abandoned` entries from the Question Bank here
- For each item, record "why it could not be resolved", "current inference",
  "what is needed to resolve it in the future"

---

## Customisation guidance

This template assumes a standard client-side GUI app. Customise as the actual
project requires.

### Offline-first / sync-heavy
- Expand Chapter 5 with conflict-resolution and queue semantics.

### Mobile-only with heavy native modules
- Split Chapter 7 into per-OS sections (iOS vs Android permissions/behaviour).

### Desktop-only
- Emphasise window management, multi-window, tray, and file associations in
  Chapters 3 and 7; trim mobile packaging rows from Chapter 8.

### Also ships a web build
- Add a web-specific section to Chapter 8 and note `web-app.md` for any
  server-rendered companion.

Customisation is finalised in dialogue with the user after Phase 1 template
selection.
