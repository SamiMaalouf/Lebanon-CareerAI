"use client";

import { useEffect, useState } from "react";
import { Panel, SimpleBarChart } from "../../components/Charts";
import { apiGet } from "../../lib/api";

export default function MarketPage() {
  const [skills, setSkills] = useState<{ name: string; pct: number }[]>([]);
  const [locations, setLocations] = useState<{ name: string; count: number }[]>([]);
  const [industries, setIndustries] = useState<{ name: string; count: number }[]>([]);
  const [education, setEducation] = useState<{ name: string; count: number }[]>([]);
  const [experience, setExperience] = useState<{ name: string; count: number }[]>([]);
  const [languages, setLanguages] = useState<{ name: string; count: number }[]>([]);
  const [categories, setCategories] = useState<{ name: string; count: number }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiGet<{ skills: { skill: string; pct: number }[] }>("/api/market/skills"),
      apiGet<{ locations: { name: string; count: number }[] }>("/api/market/locations"),
      apiGet<{ industries: { name: string; count: number }[] }>("/api/market/industries"),
      apiGet<{ education: { name: string; count: number }[] }>("/api/market/education"),
      apiGet<{ experience: { name: string; count: number }[] }>("/api/market/experience"),
      apiGet<{ languages: { name: string; count: number }[] }>("/api/market/languages"),
      apiGet<{ categories: { name: string; count: number }[] }>("/api/market/by-category"),
    ])
      .then(([sk, loc, ind, edu, exp, lang, cat]) => {
        setSkills(sk.skills.map((s) => ({ name: s.skill, pct: s.pct })));
        setLocations(loc.locations);
        setIndustries(ind.industries);
        setEducation(edu.education);
        setExperience(exp.experience);
        setLanguages(lang.languages);
        setCategories(cat.categories);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (error) return <p className="text-cedar">{error}</p>;
  if (loading) return <p className="text-ink/60">Loading market charts…</p>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-4xl text-cedar">Engineering Job Market</h1>
        <p className="mt-2 text-ink/65">
          Demand signals from real Lebanese engineering jobs and internships.
        </p>
        <p className="mt-2 text-ink/65">
          Interactive view of skill, location, industry, education, experience, and language
          demand in the collected Lebanese postings.
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Skill frequency (%)">
          <SimpleBarChart data={skills.slice(0, 15)} valueKey="pct" />
        </Panel>
        <Panel title="Jobs by career category">
          <SimpleBarChart data={categories.slice(0, 15)} />
        </Panel>
        <Panel title="Geographic distribution">
          <SimpleBarChart data={locations} />
        </Panel>
        <Panel title="Industries">
          <SimpleBarChart data={industries.slice(0, 12)} />
        </Panel>
        <Panel title="Education requirements">
          <SimpleBarChart data={education} />
        </Panel>
        <Panel title="Experience requirements">
          <SimpleBarChart data={experience} />
        </Panel>
        <Panel title="Language requirements">
          <SimpleBarChart data={languages} />
        </Panel>
      </div>
    </div>
  );
}
