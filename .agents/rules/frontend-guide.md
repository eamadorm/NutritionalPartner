---
trigger: always_on
glob: "**/*.{ts,tsx,js,jsx,vue}"
description: "Frontend standards: React/Next.js architecture, TypeScript safety, and UX/UI principles."
---

# frontend-guide.md

As a Senior Frontend Developer & UX/UI Lead, adhere to these protocols and the universal standards defined in `@.agents/rules/coding-guide.md` for building high-performance, accessible, and maintainable web interfaces:

### Environment & Tooling
- **Package Management**: Use `pnpm` or `bun` for fast, deterministic installations. 
- **Framework**: Prefer **Next.js (App Router)** with **TypeScript** for robust routing and SSR/SSG capabilities.
- **Styling**: Use **Tailwind CSS** for utility-first styling. Follow a **Mobile-First** approach using responsive modifiers (e.g., `md:`, `lg:`).

### Component Architecture
- **Atomic Design**: Separate components into `atoms` (buttons, inputs), `molecules` (search bars), and `organisms` (navbars, forms).
- **Functional Components**: Use functional components with Hooks. Keep components under **100 lines**; if exceeded, extract logic into custom hooks (e.g., `useFileData.ts`).
- **Props Validation**: Every component must have a TypeScript interface defining its props. Never use `any`.

### UX/UI Principles
- **Accessibility (A11y)**: Use semantic HTML (`<main>`, `<nav>`, `<section>`). Every image must have an `alt` tag, and buttons must have discernible text or `aria-label`.
- **Loading States**: Always implement skeleton screens or loading spinners for asynchronous data fetching to prevent layout shift.
- **Feedback Loops**: Provide immediate visual feedback for user actions (hover states, active states, and toast notifications for errors/success).
- **Consistency**: Use a centralized `theme` or Tailwind config for colors, spacing (multiples of 4px), and typography.

### Data Handling & Type Safety
- **Schema Validation**: Use **Zod** to validate API responses at the edge. This is the frontend equivalent of Pydantic.
- **API Pattern**: Mirror the Backend's Request/Response pattern. Create interfaces for `ActionRequest` and `ActionResponse`.
- **State Management**: Use **Zustand** for global state or **React Context** for low-frequency updates. Avoid prop drilling beyond 3 levels.

### Naming Conventions
- **Components/Interfaces**: `PascalCase` (e.g., `UserDashboard`, `FileUploaderProps`).
- **Variables/Hooks/Methods**: `camelCase` (e.g., `isDropdownOpen`, `useAuth`).
- **Files**: Match the component name (e.g., `UserCard.tsx`).

### Implementation Example
```tsx
import { z } from 'zod';

// Schema for API validation (Zod)
const UserProfileSchema = z.object({
  id: z.string().uuid(),
  username: z.string().min(3),
  email: z.string().email(),
});

type UserProfile = z.infer<typeof UserProfileSchema>;

interface UserCardProps {
  user: UserProfile;
  isAdmin: boolean;
}

/**
 * UserCard Component
 * Handles the display of user profile information with access-level indicators.
 */
export const UserCard = ({ user, isAdmin }: UserCardProps) => {
  return (
    <div className="p-4 border rounded-lg shadow-sm hover:border-blue-500 transition-colors">
      <h3 className="text-lg font-bold text-gray-900">{user.username}</h3>
      <p className="text-sm text-gray-600">{user.email}</p>
      {isAdmin && (
        <span className="mt-2 inline-block px-2 py-1 text-xs bg-red-100 text-red-700 rounded">
          Admin Access
        </span>
      )}
    </div>
  );
};
