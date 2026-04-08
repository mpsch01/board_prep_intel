/**
 * POST /api/scores/upload — Receives a resident score report PDF.
 *
 * Flow:
 *   1. Validate auth (resident or admin only)
 *   2. Parse multipart form data — expects fields: file, examYear
 *   3. Upload PDF to Supabase Storage (score-reports/{userId}/{examYear}/{filename})
 *   4. Create a score_uploads row (status = 'pending')
 *   5. Trigger the Railway PDF parsing microservice via webhook
 *   6. Return the upload ID so the client can poll for completion
 */
import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: profile } = await supabase
    .from("user_profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (!profile || !["resident", "admin"].includes(profile.role)) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  // Parse multipart form data
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json({ error: "Invalid form data" }, { status: 400 });
  }

  const file = formData.get("file") as File | null;
  const examYearRaw = formData.get("examYear");

  if (!file || file.type !== "application/pdf") {
    return NextResponse.json({ error: "A PDF file is required" }, { status: 400 });
  }

  const examYear = Number(examYearRaw);
  if (!examYear || examYear < 2018 || examYear > 2030) {
    return NextResponse.json({ error: "Valid examYear (2018–2030) is required" }, { status: 400 });
  }

  // Upload to Supabase Storage
  const adminClient = await createAdminClient();
  const storagePath = `score-reports/${user.id}/${examYear}/${file.name}`;
  const fileBuffer = Buffer.from(await file.arrayBuffer());

  const { error: storageError } = await adminClient.storage
    .from("score-reports")
    .upload(storagePath, fileBuffer, {
      contentType: "application/pdf",
      upsert: true,
    });

  if (storageError) {
    console.error("Storage upload error:", storageError);
    return NextResponse.json({ error: "File upload failed" }, { status: 500 });
  }

  // Create score_uploads audit row
  const { data: uploadRow, error: dbError } = await adminClient
    .from("score_uploads")
    .insert({
      resident_id: user.id,
      exam_year: examYear,
      storage_path: storagePath,
      parse_status: "pending",
    })
    .select("id")
    .single();

  if (dbError || !uploadRow) {
    console.error("DB insert error:", dbError);
    return NextResponse.json({ error: "Database error" }, { status: 500 });
  }

  // Trigger Railway parsing microservice
  const parserUrl = process.env.SCORE_PARSER_API_URL;
  const parserSecret = process.env.SCORE_PARSER_API_SECRET;

  if (parserUrl) {
    try {
      await fetch(`${parserUrl}/parse-score-report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Parser-Secret": parserSecret ?? "",
        },
        body: JSON.stringify({
          upload_id: uploadRow.id,
          resident_id: user.id,
          exam_year: examYear,
          storage_path: storagePath,
        }),
      });
    } catch (triggerErr) {
      // Log but don't fail — parsing is async, resident can poll
      console.error("Parser trigger error:", triggerErr);
    }
  }

  return NextResponse.json({
    uploadId: uploadRow.id,
    status: "pending",
    message: "File uploaded. Parsing will complete within a few minutes.",
  });
}
