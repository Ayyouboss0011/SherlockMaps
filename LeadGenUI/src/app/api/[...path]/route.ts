import { NextRequest, NextResponse } from "next/server";

// Proxies /api/* to the crawler API, stripping the /api prefix.
// CRAWLER_API_URL is read at runtime (server-side), so the same image works
// in Docker (http://crawler:8000) and locally (http://localhost:6970).
const CRAWLER_API_URL = process.env.CRAWLER_API_URL || "http://localhost:6970";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "transfer-encoding",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "upgrade",
]);

async function proxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `${CRAWLER_API_URL}/${path}${req.nextUrl.search}`;

  let body: ArrayBuffer | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.arrayBuffer();
  }

  const upstream = await fetch(url, {
    method: req.method,
    headers: {
      "Content-Type": "application/json",
    },
    body,
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      responseHeaders.set(key, value);
    }
  });

  const responseBody = await upstream.arrayBuffer();
  return new NextResponse(responseBody, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
