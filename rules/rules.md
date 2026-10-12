---
trigger: always_on
---

# Web Development Rules (React + TypeScript)

These rules govern all development work in `src/` of this repo. Every developer, agent, and AI assistant must follow them without exception. Violations caught in review are grounds for rejection.

## How to cite a rule in a PR review

Every rule has a **stable ID** (e.g. `B3.1`, `F1.2`). In a PR comment, cite the rule by its ID so the author knows exactly what to fix:

> "Violates **D1.2** — hard-coded toast string in component."

Each category also lists its **enforcement mechanism** (ESLint / `tsc` / review-only) so you know whether CI will catch it.

## Table of Contents

- [A. Architecture & Module Structure](#a-architecture--module-structure)
- [B. TypeScript & Type Safety](#b-typescript--type-safety)
- [C. Naming](#c-naming)
- [D. Constants & Domain Values](#d-constants--domain-values)
- [E. Components & UI Reuse](#e-components--ui-reuse)
- [F. Styling & Theme](#f-styling--theme)
- [G. API Layer](#g-api-layer)
- [H. JSX & Control Flow](#h-jsx--control-flow)
- [I. Code Quality](#i-code-quality)
- [J. Utilities & Repetition](#j-utilities--repetition)
- [K. Imports](#k-imports)
- [L. Error Handling](#l-error-handling)
- [M. Performance](#m-performance)
- [N. Security](#n-security)
- [O. Testing](#o-testing)
- [P. Git & Commits](#p-git--commits)
- [Enforcement Matrix](#enforcement-matrix)
- [PR Review Checklist](#pr-review-checklist)

---

## A. Architecture & Module Structure

Enforcement: **review-only**.

### A1. Feature modules live in `src/modules/`

- **A1.1** Every feature is a self-contained module at `src/modules/<feature>/`.
- **A1.2** A module owns its own: components, context, API, types, constants, utils, styles.
- **A1.3** Cross-module imports are allowed only through explicit public entry points (`index.ts` or the named context hook / API function).

### A2. File layout

- **A2.1** Single-component modules may keep the component at the module root.
- **A2.2** **Multi-component modules must put every component under `<module>/components/`.** Only components go in `components/`. Hooks (`use*.ts`), API (`<module>Api.ts`), types, constants, utils, and `<module>.styles.ts` stay at the **module root** so imports remain flat and predictable.

```
modules/
  faq/
    Faq.tsx                 # Entry component (wraps children in Provider)
    FaqContext.tsx          # Provider + useFaqContext hook
    faqApi.ts               # API functions
    faq.types.ts            # Interfaces / unions
    faq.constants.ts        # All constants + `as const` domain objects + structured mappings
    faq.styles.ts           # sx objects (see F1)
    faqUtils.ts             # Pure helpers
    components/
      FaqList.tsx
      FaqItem.tsx
      FaqFilters.tsx
```

### A3. Context architecture

- **A3.1** A module may have **one or more contexts**, but keep them few and intentional. Group things that naturally belong together; don't split for the sake of splitting.
- **A3.2** **The context value must expose only state and handlers** — nothing else. No helper functions, no pure derivations, no formatting utilities on the context object.
- **A3.3** Pure helpers / derivations live in `<module>Utils.ts` and are imported directly where needed. They never ride on the context.
- **A3.4** Each submodule owns its own state, effects, and logic via a **submodule hook** (`useFaqListState`, `useFaqFormState`, etc.). Compose these hooks inside the provider; expose each as a named slice.
- **A3.5** When growth forces a split, **add more submodule hooks first**. Create a second context only when a clear boundary or independent usage emerges.
- **A3.6** Consumers should call a **narrow custom hook** (e.g. `useFaqListSlice()`) that reads the root context and returns only the required values. Never pass the full context down.
- **A3.7** Context value wrapped in `useMemo`; callbacks wrapped in `useCallback` (see M1, M2).

```tsx
import { createContext, useContext, useMemo, useState, type PropsWithChildren } from "react";

type SubModule1State = {
  count: number;
  trigger: () => void;
};

function useSubModule1(): SubModule1State {
  const [count, setCount] = useState(0);
  const trigger = () => setCount((c) => c + 1);
  return { count, trigger };
}

type ModuleContextValue = {
  moduleName: string;
  setModuleName: (name: string) => void;
  subModule1: SubModule1State;
};

const ModuleContext = createContext<ModuleContextValue | null>(null);

export function ModuleContextProvider({ children }: PropsWithChildren) {
  const [moduleName, setModuleName] = useState("");
  const subModule1 = useSubModule1();

  const value = useMemo<ModuleContextValue>(
    () => ({ moduleName, setModuleName, subModule1 }),
    [moduleName, subModule1],
  );

  return <ModuleContext.Provider value={value}>{children}</ModuleContext.Provider>;
}

export function useModuleContext(): ModuleContextValue | null {
  return useContext(ModuleContext);
}

export function useSubModule1Slice(): SubModule1State | null {
  const ctx = useModuleContext();
  return ctx?.subModule1 ?? null;
}
```

### A4. State management migration

- **A4.1** New code must use `useContext` + hooks. **No new Redux slices or Zustand stores.**
- **A4.2** Existing Redux (`src/store/slices/`) and Zustand (`src/zustand/`) code is tolerated only in legacy modules pending migration.
- **A4.3** Do not re-introduce `useFormContext` / `react-hook-form` — it was removed by decision.

---

## B. TypeScript & Type Safety

Enforcement: **ESLint + `tsc --noEmit`**. Most violations here fail CI.

### B1. Explicit types everywhere

- **B1.1** Every variable, parameter, return value, state, prop, and API response has an explicit TypeScript type.
- **B1.2** API response types separate the axios wrapper from the domain payload.
- **B1.3** Prefer discriminated unions over loose string fields for statuses.

### B2. Forbidden escape hatches

- **B2.1** Forbidden: `any`, `unknown`, `as any`, `as unknown`.
- **B2.2** Forbidden: `@ts-ignore`, `@ts-expect-error`.
- **B2.3** Forbidden: `as` type assertions without a preceding runtime check.
- **B2.4** Forbidden: implicit `any` leaking from untyped library calls (e.g. untyped axios responses).

### B3. No `keyof` / `typeof` in type positions

- **B3.1** The `keyof` keyword is forbidden in types.
- **B3.2** The `typeof` keyword is forbidden **in type positions** (e.g. `type T = typeof FOO`, `ReturnType<typeof fn>`). Runtime `typeof x === "..."` in expressions is fine — this ban is about type-level usage only.
- **B3.3** Replace derived patterns like `(typeof OBJ)[keyof typeof OBJ]` with an **explicitly declared** string literal union next to the `as const` object (see D2).
- **B3.4** For hook return types, declare a named state type and annotate the hook's return — do **not** use `ReturnType<typeof useXxx>`.

Enforced by ESLint `no-restricted-syntax` → `TSKeyOfKeyword` and `TSTypeQuery` are `error`.

### B4. Interface / type naming

- **B4.1** Feature-prefixed, never generic `Props`: `FaqItemProps`, `FaqListState`.
- **B4.2** When the `as const` object and the union type would share a name, use `FOO_STATUS` for the object and `FooStatus` for the type (see D2).

---

## C. Naming

Enforcement: **review-only** (some covered by ESLint when obvious).

### C1. Files & folders

| What              | Convention             | Example                       |
| ----------------- | ---------------------- | ----------------------------- |
| Folders           | `kebab-case`           | `faq/`, `gate-pass/`          |
| Component files   | `PascalCase.tsx`       | `FaqItem.tsx`, `PollView.tsx` |
| Hook files        | `camelCase.ts`         | `useActiveContext.ts`         |
| Utility files     | `camelCase.ts`         | `faqUtils.ts`                 |
| Type files        | `camelCase.ts`         | `faq.types.ts`                |
| Constant files    | `camelCase.ts`         | `faq.constants.ts`            |
| Styles files      | `camelCase.ts`         | `faq.styles.ts`               |

### C2. Identifiers

| What              | Convention                 | Example                                |
| ----------------- | -------------------------- | -------------------------------------- |
| Constants         | `SCREAMING_SNAKE_CASE`     | `FAQ_POPULAR_THRESHOLD`                |
| Booleans          | `is/has/should/can` prefix | `isLoading`, `hasError`, `shouldFetch` |
| Event handlers    | `handle` prefix            | `handleSubmit`, `handleToggle`         |
| Variables         | Domain-meaningful          | `faqItem`, `searchQuery`               |
| Component exports | Match file name            | `FaqItem.tsx` → `export FaqItem`       |

### C3. Forbidden vague names

- **C3.1** No `data`, `item`, `temp`, `value`, `result`, `info`, `obj` without a domain prefix.

---

## D. Constants & Domain Values

Enforcement: **review-only** (the structural pattern is ESLint-friendly once linter rules are added).

### D1. No hard-coded domain values in components or functions

- **D1.1** Components and functions must not contain raw domain strings inline — labels, titles, toast messages, error messages, aria labels, route paths, API paths, query keys, option values, status values, etc.
- **D1.2** All such strings live in `<module>.constants.ts` (or a cross-module constants file when shared). **There is no separate `.config.ts` file** — structured mappings (enum → label / class / icon / handler maps, form configs) also live in `<module>.constants.ts`.
- **D1.3** Also applies to numbers: thresholds, page sizes, debounce durations, etc.
- **D1.4** Exception: Tailwind utility classes directly in `className` and single-character decorative JSX glyphs.
- **D1.5** Reusable Tailwind combinations (e.g. a button-variant class) must still be named constants.

### D2. `as const` object + explicit union type

Forbidden: `export enum` (incompatible with `erasableSyntaxOnly` — TS 5.8+).

Required pattern: runtime `as const` object + explicit string literal union (no `keyof` / `typeof` — see B3).

```ts
export const AUTH_STATUS = {
  LOADING: "loading",
  AUTHENTICATED: "authenticated",
  UNAUTHENTICATED: "unauthenticated",
} as const;

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";
```

- **D2.1** All logic, props, context, and API mappings must use the `CONST_OBJECT.MEMBER` values (e.g. `AUTH_STATUS.LOADING`). Never raw string literals for those domains.
- **D2.2** Never derive the union with `(typeof OBJ)[keyof typeof OBJ]` (violates B3).
- **D2.3** Inline string comparisons like `status === "loading"` are forbidden — compare to the const member.

### D3. Cross-module domain state

- **D3.1** State that identifies **which** shared UI surface is active (header panels, drawers, modals, etc.) is a domain string state and owned by one module's constants file.
- **D3.2** The **owning module** exports the `as const` object and the explicit union type.
- **D3.3** **Consumer modules** import the const object and reference `OBJ.MEMBER` — never inline the literal.
- **D3.4** `null` for "nothing active" stays `null` and is not a domain value.

```ts
// src/modules/header/header.constants.ts
export const HEADER_EXCLUSIVE_PANEL = {
  NOTIFICATIONS: "notifications",
  PROFILE: "profile",
} as const;

export type HeaderExclusivePanelId = "notifications" | "profile";
export type HeaderExclusivePanel = HeaderExclusivePanelId | null;
```

---

## E. Components & UI Reuse

Enforcement: **review-only**.

### E1. Props & shape

- **E1.1** Props interfaces are feature-prefixed (`FaqItemProps`), never generic `Props`.
- **E1.2** Components are small, focused, composable.
- **E1.3** Within a feature module, child components read from context (via the hook) rather than prop-drilling.
- **E1.4** Exception to E1.3: pure presentational components intentionally decoupled from context may take props.
- **E1.5** All non-submit `<button>` elements need `type="button"`.

### E2. Reuse from `ui-components/` (mandatory)

- **E2.1** Any component that is reusable — buttons, chips, modals, text fields, textareas, empty states, tabs, breadcrumbs, avatars, infinite scrolls, form field parts, snackbars, etc. — **must** come from `src/modules/ui-components/`.
- **E2.2** Before writing a new primitive in a feature module, check `src/modules/ui-components/`. If a suitable component exists, use it.
- **E2.3** If a reusable primitive is missing, add it to `ui-components/` (not to the feature module) and then consume it.
- **E2.4** Feature modules must not re-implement primitives inline (no local `<button className="...">` styled to look like a primary button — use the shared primitive).

---

## F. Styling & Theme

Enforcement: **review-only** (F1 file-existence is mechanically checkable).

### F1. Mandatory `<module>.styles.ts`

- **F1.1** Every feature module that renders UI must have a **`<module>.styles.ts`** file at the module root — alongside `<module>Api.ts` and `<module>.constants.ts`.
- **F1.2** All `sx` objects, layout rules, spacing, color, typography, radius, and shadow values live in `<module>.styles.ts` — **not inline in components**.
- **F1.3** Colocate styles at the **module root**, not inside `components/`.
- **F1.4** Build styles with `createStyles` from `@/modules/theme/theme.utils`. It accepts an object whose values are plain `sx` objects or `(theme: Theme) => …` callbacks.
- **F1.5** Import `Theme` as a type only: `import type { Theme } from "@/modules/theme/theme.types"`.
- **F1.6** Export one named styles object per module (`faqStyles`, `profileStyles`) and consume as `sx={faqStyles.page}` or `sx={{ ...faqStyles.header, bgcolor: dynamicColor }}` when a value must remain in the component.

### F2. Theme tokens only from `src/modules/theme/`

- **F2.1** All theme tokens (colors, palette, typography, spacing, radii, breakpoints) come from `src/modules/theme/`.
- **F2.2** No hard-coded `#hex`, `rgb(...)`, magic `px` sizes, or custom font stacks in components or styles files — pull from theme via `(theme) => theme.palette...`, `theme.spacing(...)`, `theme.typography...`.
- **F2.3** Light/dark palette objects live in `muiThemePalette.constants.ts`. Extend the MUI theme when a new token is needed — do not scatter `createTheme` calls.
- **F2.4** Do not duplicate palette or body / `#root` rules in CSS; base document styles come from MUI `CssBaseline` in `ThemeContext.tsx`.

### F3. Tailwind rules

- **F3.1** Tailwind is the primary utility styling approach.
- **F3.2** Tailwind class names must be **complete, static strings** — never interpolated dynamically (`bg-${color}-500` breaks JIT).
- **F3.3** Use a class-mapping object for dynamic variants.
- **F3.4** No inline `style` objects unless Tailwind genuinely cannot express the dynamic value.
- **F3.5** Do not use the MUI `sx` prop for things Tailwind can express — reserve `sx` for MUI-component specifics via `<module>.styles.ts`.
- **F3.6** Migration target: move remaining Radix UI usage to MUI.

---

## G. API Layer

Enforcement: **review-only + `tsc`** (return types caught by the type checker).

### G1. Per-module API

- **G1.1** Each module defines its own API functions in `<module>Api.ts`.
- **G1.2** Endpoint URLs are constants inside the module.

### G2. Return types & unwrapping

- **G2.1** API functions have **explicit return types**. Never leak implicit `any` from axios.
- **G2.2** API functions return **unwrapped domain data** — the consumer should not chain `.data.data`.

### G3. Shared axios instance

- **G3.1** Import the shared `axiosInstance` from `src/modules/axios/axiosInstance.ts`. No ad-hoc `axios.create` in feature code.
- **G3.2** Its `baseURL` is `appConfig.apiV1BaseUrl` (`VITE_BASE_URL + "/api/v1"`, see `src/modules/config/app/app.config.ts`).
- **G3.3** The Bearer token is attached from `authUserManager` in `src/modules/auth/auth.config.ts`. Response interceptors handle common statuses (`src/modules/axios/axios.constants.ts`, `axios.types.ts`).

### G4. Non-React toasts

- **G4.1** Global API error toasts use `src/modules/toast/toastService.ts`. `ToastProvider` in `src/modules/toast/ToastContext.tsx` subscribes and renders MUI snackbar UI.
- **G4.2** Interceptors must **not** import React.

### G5. Domain user vs OIDC profile

- **G5.1** Backend user details are loaded via `fetchUserDetails()` in `src/modules/auth/authApi.ts` (e.g. `GET /user`).
- **G5.2** OIDC profile is for SSO only. App-facing user fields live on `AuthContext` as `userDetails`.

---

## H. JSX & Control Flow

Enforcement: **review-only**.

- **H1.1** Only **single-level** ternary operators inside JSX return blocks.
- **H1.2** Forbidden inside JSX: nested ternaries, `if/else` expressions, `switch`, multi-branch logic.
- **H1.3** Complex conditions are computed as variables or helper functions **before** `return`.
- **H1.4** Prefer early returns for error / loading / empty states over deep nesting.

---

## I. Code Quality

Enforcement: **review-only**.

### I1. Function shape & size

- **I1.1** One thing per function. If a function needs a comment explaining "what", rename or split it.
- **I1.2** Target under 50 lines per function. Extract sub-functions when logic grows.
- **I1.3** No dead code, commented-out code, empty `finally` blocks, or pointless `catch` → rethrow.
- **I1.4** No premature abstraction. Three similar lines are better than a premature generic helper.
- **I1.5** Solve the current problem, not hypothetical future ones.

### I2. No unnecessary comments

- **I2.1** Do not add comments that narrate what the code does. Self-explanatory code needs no commentary.
- **I2.2** Forbidden examples: `// increment counter`, `// import module`, `// return result`, `// handle error`, `// fetch data`, `// render component`, `// map over items`, `// set state`.
- **I2.3** Comments are only acceptable when they convey **non-obvious intent, trade-offs, or constraints** that the code itself cannot express — for example, a workaround for a known library bug, an invariant the type system cannot encode, or a rationale for a chosen algorithm.
- **I2.4** Do not use comments to explain the change you are making in a PR; that belongs in the commit message or PR description.
- **I2.5** Never leave TODO / FIXME / XXX comments without a linked ticket ID (e.g. `// TODO(ENG-1234): ...`). Unlinked markers are dead weight and must be resolved or filed.
- **I2.6** Prefer a **well-named function or variable** over a comment. If you feel the need to write `// calculate total`, rename the expression into a `totalAmount = ...` or extract `calculateTotal()`.
- **I2.7** JSDoc is only required on **exported public APIs** where a consumer outside the module will use it without reading the source (e.g. a shared util in `ui-components/` or a cross-module hook). Internal functions do not need JSDoc.

---

## J. Utilities & Repetition

Enforcement: **review-only**.

- **J1.1** Identical or near-identical logic across files must be extracted to a shared utility.
- **J1.2** Common logic (formatting, filtering, mapping, validation) belongs in `<module>Utils.ts`, never in components or context providers.
- **J1.3** Use `date-fns` exclusively for dates. **`moment` is forbidden anywhere.**
- **J1.4** `date-fns` may only be imported inside `*Utils.ts` files. Components call the util.

---

## K. Imports

Enforcement: **ESLint** (`import/order`).

Imports follow this exact order with blank lines between groups:

```ts
// 1. React / React DOM
import { useCallback, useState } from "react";

// 2. External libraries (npm packages)
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";

// 3. Internal aliases (@/ paths)
import { Button } from "@/modules/ui-components";
import { capitalizeFirstLetter } from "@/utils/helper";

// 4. Relative imports (same module)
import { useFaqContext } from "./FaqContext";
import { FAQ_TITLE } from "./faq.constants";
```

- **K1.1** Four groups, blank-line separated.
- **K1.2** `unused-imports/no-unused-imports` → `error`. Clean up before commit.

---

## L. Error Handling

Enforcement: **review-only** (console.log rule is ESLint-friendly to add).

- **L1.1** API errors must be caught and surfaced to the user via toast (`toastService`) or inline error state.
- **L1.2** Error state is **meaningful**: store the error message, not just a boolean.
- **L1.3** Never silently swallow errors with an empty catch block.
- **L1.4** `console.log` is allowed **only inside `catch` blocks**. Banned everywhere else.
- **L1.5** React context hooks like `useXxxContext()` must **not** throw when used outside a provider. Return `null` (or a defined sentinel), and let callers guard with early-return / spinners. (See `.cursor/rules/react-context.mdc`.)

---

## M. Performance

Enforcement: **review-only**.

- **M1.1** Context values must be wrapped in `useMemo` (see A3.7).
- **M1.2** Callbacks passed through context must be wrapped in `useCallback`.
- **M1.3** Expensive derived data (filtered lists, aggregations) must use `useMemo`.
- **M1.4** Lists with more than ~50 items should consider virtualization (`react-virtual`).

---

## N. Security

Enforcement: **review-only**.

- **N1.1** Never render user-generated content with `dangerouslySetInnerHTML` without sanitization (DOMPurify).
- **N1.2** Never log sensitive data (tokens, passwords, PII) — not even in `catch` blocks.
- **N1.3** Never commit `.env` files, credentials, or API keys.
- **N1.4** Validate and sanitize all user input at system boundaries.
- **N1.5** Use `import.meta.env.VITE_*` only — never `process.env` in app code.

---

## O. Testing

Enforcement: **review-only**.

- **O1.1** All utility functions (`*Utils.ts`) must have unit tests.
- **O1.2** Context providers should have integration tests validating the state machine.
- **O1.3** New features include tests. Refactored modules backfill tests.

---

## P. Git & Commits

Enforcement: **Husky + CommitLint** (runs in pre-commit).

- **P1.1** Commit messages follow Conventional Commits (CommitLint).
- **P1.2** Pre-commit hooks (Husky + lint-staged) must pass before committing.
- **P1.3** Never use `--no-verify` to bypass hooks.
- **P1.4** Never force-push to `main`.

---

## Enforcement Matrix

| Category                          | ESLint | `tsc` | Husky | Review |
| --------------------------------- | :----: | :---: | :---: | :----: |
| A. Architecture                   |        |       |       |   ✓    |
| B. TypeScript (B1, B2)            |   ✓    |   ✓   |       |   ✓    |
| B3. No keyof / typeof             |   ✓    |       |       |   ✓    |
| C. Naming                         |        |       |       |   ✓    |
| D. Constants & domain values      |        |       |       |   ✓    |
| E. Components & UI reuse          |        |       |       |   ✓    |
| F. Styling & theme                |        |       |       |   ✓    |
| G. API layer (return types)       |        |   ✓   |       |   ✓    |
| H. JSX & control flow             |        |       |       |   ✓    |
| I. Code quality                   |        |       |       |   ✓    |
| J. Utilities (date-fns, moment)   |        |       |       |   ✓    |
| K. Imports                        |   ✓    |       |       |        |
| L. Error handling                 |        |       |       |   ✓    |
| M. Performance                    |        |       |       |   ✓    |
| N. Security                       |        |       |       |   ✓    |
| O. Testing                        |        |       |       |   ✓    |
| P. Commits                        |        |       |   ✓   |        |

---

## PR Review Checklist

Top items to scan for, grouped by category ID:

1. **A2.2** — multi-component module: are all components under `components/`?
2. **A3.2 / A3.3** — any helpers on the context value? move to utils.
3. **B2** — any `any`, `as any`, `@ts-ignore`?
4. **B3** — any `keyof` or type-position `typeof` (including `ReturnType<typeof ...>`)?
5. **D1** — any inline domain strings / numbers in components or functions?
6. **D2** — does every status/mode use the `CONST.MEMBER` pattern with an explicit union?
7. **E2** — are buttons / chips / modals reused from `ui-components/` or re-invented locally?
8. **F1** — does the module have a `<module>.styles.ts`? Any inline `sx` in components?
9. **F2** — any hard-coded `#hex` / `px` tokens outside the theme module?
10. **G2** — API functions: explicit return types, unwrapped payloads?
11. **G3** — ad-hoc `axios.create` instead of shared `axiosInstance`?
12. **H1** — nested ternaries or complex branching inside JSX?
13. **K1** — import groups ordered and blank-line separated?
14. **L1.4** — `console.log` outside a `catch` block?
15. **M1** — context value in `useMemo`, callbacks in `useCallback`?
16. **I2** — narrating comments (`// fetch data`, `// render component`) that should be deleted?

---

## Summary of Forbidden Patterns

| Pattern                                        | Rule  | Why                                    |
| ---------------------------------------------- | ----- | -------------------------------------- |
| `any`, `unknown`, `as any`                     | B2.1  | Defeats type safety                    |
| `@ts-ignore` / `@ts-expect-error`              | B2.2  | Fix the type, don't suppress           |
| `keyof` / type-position `typeof`               | B3    | Use explicit string literal unions     |
| Narrating / obvious comments                   | I2    | Code should self-document              |
| Unlinked `TODO` / `FIXME` / `XXX`              | I2.5  | Must reference a ticket or be resolved |
| Helpers / pure functions on context value      | A3.2  | Context = state + handlers only        |
| Local re-implementation of shared primitives   | E2    | Use `ui-components/`                   |
| Inline `sx` or hard-coded design tokens        | F1/F2 | Use `<module>.styles.ts` + theme       |
| Inline domain strings in components/functions  | D1    | Move to `<module>.constants.ts`        |
| Multi-component module without `components/`   | A2.2  | Nest components in `components/`       |
| `export enum`                                  | D2    | Incompatible with `erasableSyntaxOnly` |
| `moment`                                       | J1.3  | Replaced by `date-fns`                 |
| `useFormContext` / `react-hook-form`           | A4.3  | Removed by decision                    |
| New Redux slices / Zustand stores              | A4.1  | Migration to Context                   |
| Nested ternaries in JSX                        | H1.2  | Unreadable                             |
| `console.log` outside catch                    | L1.4  | Use toast/logger or remove             |
| `dangerouslySetInnerHTML` without sanitization | N1.1  | XSS risk                               |
| Dynamic Tailwind class interpolation           | F3.2  | Breaks JIT compiler                    |
| `process.env` in app code                      | N1.5  | Use `import.meta.env.VITE_*`           |