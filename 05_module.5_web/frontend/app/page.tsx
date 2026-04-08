/**
 * Landing page / login redirect.
 * Authenticated users are sent to their role-appropriate dashboard.
 */
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function HomePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  const role = profile?.role ?? "resident";

  if (role === "admin") redirect("/admin/users");
  if (role === "faculty") redirect("/faculty/search");
  redirect("/resident/dashboard");
}
