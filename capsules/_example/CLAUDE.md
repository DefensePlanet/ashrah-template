# Example Capsule

This is a starter capsule to show you the pattern. Rename this directory and customize.

## What This Is

A capsule is a self-contained project workspace. When you `cd` into this directory and run `claude`, it loads this `CLAUDE.md` on top of the system-level `CLAUDE.md`. Your orchestrator gets project-specific context without seeing anything from your other projects.

## Project Context

<!-- Replace with your project details -->

**Name:** My App
**Stack:** React, TypeScript, Supabase
**Description:** A brief description of what this project does.

## Key Decisions

<!-- Document important technical choices so your AI remembers them -->

- **Auth:** Supabase Auth with row-level security
- **Styling:** Tailwind CSS + shadcn/ui components
- **Deployment:** Vercel

## API Keys & Credentials

All credentials for this project live in `.env` (gitignored). Never commit secrets.

## Agent Notes

<!-- Optional: give agents project-specific instructions -->

When working in this capsule:
- The database schema is in `supabase/migrations/`
- UI components follow the design system in `src/components/ui/`
- All API routes are in `src/app/api/`

## File Structure

```
_example/
  CLAUDE.md       <- You are here (project context for the AI)
  .env            <- Project credentials (gitignored)
  .env.example    <- Template for required credentials
  src/            <- Your project code
  specs/          <- Feature specs, PRDs, design docs
```
