/** Shared engineering career categories for Eng. Jobs insights, Skill Gap, and CV Coach. */

export const ENGINEERING_CATEGORIES = [
  "Software Engineering",
  "Web Development",
  "Data Science",
  "Artificial Intelligence",
  "Cybersecurity",
  "Electrical Engineering",
  "Electronics Engineering",
  "Mechanical Engineering",
  "Mechatronics Engineering",
  "Automation Engineering",
  "Robotics",
  "Civil Engineering",
  "Architecture",
] as const;

export type EngineeringCategory = (typeof ENGINEERING_CATEGORIES)[number];

const CATEGORY_ALIASES: Record<string, EngineeringCategory> = {
  "Computer Engineering": "Software Engineering",
};

export function defaultEngineeringCategory(
  preferred?: string[] | null,
  fallback: EngineeringCategory = "Software Engineering"
): EngineeringCategory {
  for (const c of preferred || []) {
    const mapped = CATEGORY_ALIASES[c] || c;
    if ((ENGINEERING_CATEGORIES as readonly string[]).includes(mapped)) {
      return mapped as EngineeringCategory;
    }
  }
  return fallback;
}
