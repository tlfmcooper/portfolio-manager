# Tasks: Landing Page for InvestSmart

**Input**: Design documents from `specs/002-build-a-landing/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Web app**: `frontend/src/`

## Phase 3.1: Setup
- [X] T001 [P] Research best practices for responsive landing page design in React/Vite (Output to `specs/002-build-a-landing/research.md`)
- [X] T002 [P] Research best practices for integrating a new page into an existing Vite/React application (Output to `specs/002-build-a-landing/research.md`)
- [X] T003 Consolidate research findings in `specs/002-build-a-landing/research.md`

## Phase 3.2: Core Implementation - Components
- [X] T004 Create `frontend/src/components/LandingPage/Logo.jsx` for the InvestSmart logo.
- [X] T005 Create `frontend/src/components/LandingPage/NavigationMenu.jsx` for the main navigation menu.
- [X] T006 Create `frontend/src/components/LandingPage/ActionButtons.jsx` for "Log In" and "Sign Up" buttons.
- [X] T007 Create `frontend/src/components/LandingPage/HeroSection.jsx` with headline, value proposition, and CTA buttons.
- [X] T008 Create `frontend/src/components/LandingPage/KeyFeaturesSection.jsx` with title and subtitle.
- [X] T009 Create `frontend/src/pages/LandingPage.jsx` and integrate all LandingPage sub-components.

## Phase 3.3: Styling and Responsiveness
- [X] T010 Implement styling for `frontend/src/components/LandingPage/Logo.jsx` to match app design.
- [X] T011 Implement styling for `frontend/src/components/LandingPage/NavigationMenu.jsx` to match app design and ensure responsiveness.
- [X] T012 Implement styling for `frontend/src/components/LandingPage/ActionButtons.jsx` to match app design and ensure responsiveness.
- [X] T013 Implement styling for `frontend/src/components/LandingPage/HeroSection.jsx` to match app design and ensure responsiveness.
- [X] T014 Implement styling for `frontend/src/components/LandingPage/KeyFeaturesSection.jsx` to match app design and ensure responsiveness.
- [X] T015 Implement overall responsive design for `frontend/src/pages/LandingPage.jsx`.

## Phase 3.4: Integration and Functionality
- [X] T016 Implement navigation links in `frontend/src/components/LandingPage/NavigationMenu.jsx` (Overview, Risk Analytics, Asset Allocation).
- [X] T017 Implement "Log In" and "Sign Up" button functionality in `frontend/src/components/LandingPage/ActionButtons.jsx`.
- [X] T018 Implement "Get Started" and "Learn More" button functionality in `frontend/src/components/LandingPage/HeroSection.jsx`.

## Phase 3.5: Testing
- [X] T019 Write unit tests for `frontend/src/components/LandingPage/Logo.jsx` in `frontend/tests/unit/LandingPage/Logo.test.jsx`.
- [X] T020 Write unit tests for `frontend/src/components/LandingPage/NavigationMenu.jsx` in `frontend/tests/unit/LandingPage/NavigationMenu.test.jsx`.
- [X] T021 Write unit tests for `frontend/src/components/LandingPage/ActionButtons.jsx` in `frontend/tests/unit/LandingPage/ActionButtons.test.jsx`.
- [X] T022 Write unit tests for `frontend/src/components/LandingPage/HeroSection.jsx` in `frontend/tests/unit/LandingPage/HeroSection.test.jsx`.
- [X] T023 Write unit tests for `frontend/src/components/LandingPage/KeyFeaturesSection.jsx` in `frontend/tests/unit/LandingPage/KeyFeaturesSection.test.jsx`.
- [X] T024 Write integration tests for `frontend/src/pages/LandingPage.jsx` in `frontend/tests/integration/LandingPage.test.jsx` to verify content and navigation.

## Dependencies
- T001, T002 must be completed before T003.
- T004-T009 must be completed before T010-T015.
- T010-T015 must be completed before T016-T018.
- T004-T018 must be completed before T019-T024.

## Parallel Example
```
# Phase 3.1: Research tasks can run in parallel
Task: "Research best practices for responsive landing page design in React/Vite"
Task: "Research best practices for integrating a new page into an existing Vite/React application"

# Phase 3.2: Component creation tasks can run in parallel
Task: "Create frontend/src/components/LandingPage/Logo.jsx"
Task: "Create frontend/src/components/LandingPage/NavigationMenu.jsx"
...
```

## Notes
- Verify tests pass after each implementation task.
- Commit after each task.
