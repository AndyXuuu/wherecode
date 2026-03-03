# Command Center UI Spec (Active)

Updated: 2026-03-03

## 1) Scope

- Mobile-first command UI.
- Main line: `Project -> Task -> Command`.
- Async command flow only (submit + polling + approval).

## 2) Routes

Primary:
- `/overview`
- `/tasks`
- `/projects`
- `/auth`

Detail:
- `/task/[id]`
- `/project/[id]`
- `/project/[id]/settings`

Ops:
- `/command-lab` (full-stack integration page)
- `/feed` (legacy path, redirects to `/overview`)

## 3) Key capabilities in UI

- Create/list projects and tasks.
- Submit command and poll command status.
- Approve `waiting_approval` command.
- Select assignee (`auto-agent` or explicit).
- Show metrics summary and routing history.
- Show Control Center and Action Layer health probes.

## 4) Theme and style constraints

- Next.js + Tailwind.
- CSS variable theme tokens in `app/globals.css`.
- `dark/light` toggle with persisted preference.

## 5) Source files

- App routes: `command_center/app/*`
- Integration page: `command_center/components/feed-workspace.tsx`
- API client: `command_center/lib/control-center-client.ts`
- Shared types: `command_center/types/*`
