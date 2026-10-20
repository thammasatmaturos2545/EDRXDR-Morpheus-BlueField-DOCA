import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import {
  createHash,
  timingSafeEqual
} from "node:crypto";

const SECRET_FILE =
  "/home/saiuser/nexus-history-preview-20261020/preview-access.secret";

function digest(value: string): Buffer {
  return createHash("sha256")
    .update(value, "utf8")
    .digest();
}

export async function requireHistoryAuth(
  request: Request
): Promise<NextResponse | null> {
  let secret: string;

  try {
    secret = (
      await readFile(SECRET_FILE, "utf8")
    ).trim();
  } catch {
    return NextResponse.json(
      { error: "History authentication unavailable" },
      {
        status: 503,
        headers: { "Cache-Control": "no-store" }
      }
    );
  }

  if (!/^[0-9a-f]{64}$/.test(secret)) {
    return NextResponse.json(
      { error: "History authentication unavailable" },
      {
        status: 503,
        headers: { "Cache-Control": "no-store" }
      }
    );
  }

  const header =
    request.headers.get("authorization") || "";

  let credentials = "";
  let validFormat = false;

  if (header.length <= 180) {
    const match = header.match(
      /^Basic ([A-Za-z0-9+/]+={0,2})$/
    );

    if (match) {
      credentials = Buffer.from(
        match[1], "base64"
      ).toString("utf8");

      validFormat = true;
    }
  }

  const expected = "saiuser:" + secret;

  const authorized =
    validFormat &&
    timingSafeEqual(
      digest(credentials),
      digest(expected)
    );

  if (!authorized) {
    return new NextResponse(
      "Authentication required",
      {
        status: 401,
        headers: {
          "WWW-Authenticate":
            'Basic realm="NEXUS All Events", charset="UTF-8"',
          "Cache-Control": "no-store",
          "X-Content-Type-Options": "nosniff"
        }
      }
    );
  }

  return null;
}
