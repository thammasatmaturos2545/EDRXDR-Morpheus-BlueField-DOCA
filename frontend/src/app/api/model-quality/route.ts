import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import { isParityReport, isQualityReport } from "../../../lib/model-quality";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
const headers = { "Cache-Control": "no-store" };
const defaultRun = "morpheus-raw-offline-check-20261008T203523Z-1803526";

export async function GET() {
  // Configured by the operator, never derived from a URL parameter.
  const directory = process.env.MODEL_QUALITY_REPORT_DIR
    ? path.resolve(process.env.MODEL_QUALITY_REPORT_DIR)
    : path.resolve(process.cwd(), "..", "reports", defaultRun);
  try {
    const [qualityBytes, parityBytes] = await Promise.all([
      readFile(path.join(directory, "quality_report.json")),
      readFile(path.join(directory, "parity_report.json")),
    ]);
    const quality: unknown = JSON.parse(qualityBytes.toString("utf8"));
    const parity: unknown = JSON.parse(parityBytes.toString("utf8"));
    if (!isQualityReport(quality) || !isParityReport(parity) || quality.threshold !== parity.threshold) {
      throw new Error("Invalid or inconsistent report contract");
    }
    return NextResponse.json({
      run_id: path.basename(directory),
      checked_at: new Date().toISOString(),
      source: {
        quality_sha256: createHash("sha256").update(qualityBytes).digest("hex"),
        parity_sha256: createHash("sha256").update(parityBytes).digest("hex"),
      },
      quality,
      // Deliberately return only evaluation identity and parity summary, not raw source paths/logs.
      parity: {
        status: parity.status,
        rows: parity.rows,
        compared_rows: parity.compared_rows,
        max_absolute_score_error: parity.max_absolute_score_error,
        threshold: parity.threshold,
        checkpoint: path.posix.basename(parity.checkpoint),
        checkpoint_weights_sha256: parity.checkpoint_weights_sha256,
        dataset_manifest_sha256: parity.dataset_manifest_sha256,
        held_out_data_used: parity.held_out_data_used,
        raw_event_check: {
          status: parity.raw_event_check.status,
          reconstructed_rows: parity.raw_event_check.reconstructed_rows,
          held_out_data_used: parity.raw_event_check.held_out_data_used,
        },
      },
    }, { headers });
  } catch (error) {
    const missing = error instanceof Error && "code" in error && error.code === "ENOENT";
    return NextResponse.json({
      error: missing
        ? "ไม่พบไฟล์รายงาน Model Quality — ตรวจ MODEL_QUALITY_REPORT_DIR บนเซิร์ฟเวอร์"
        : "อ่านรายงาน Model Quality ไม่สำเร็จ หรือรูปแบบข้อมูลไม่สอดคล้องกัน",
    }, { status: missing ? 503 : 502, headers });
  }
}
