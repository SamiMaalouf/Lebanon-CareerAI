"use client";

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function CareersRedirectInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const params = new URLSearchParams();
    const category = searchParams.get("category");
    if (category) params.set("category", category);
    const qs = params.toString();
    router.replace(qs ? `/jobs?${qs}` : "/jobs");
  }, [router, searchParams]);

  return <p className="text-ink/60">Redirecting to Engineering Jobs…</p>;
}

export default function CareersPage() {
  return (
    <Suspense fallback={<p className="text-ink/60">Redirecting…</p>}>
      <CareersRedirectInner />
    </Suspense>
  );
}
