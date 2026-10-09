import { travelPost } from "@/lib/server/travelApi";

export async function POST(request) {
  if (request.headers.get("origin") !== new URL(request.url).origin) {
    return Response.json({ error: "Please send your enquiry from this website." }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ error: "Please check your enquiry details." }, { status: 415 });
  }
  return travelPost(request, "trips/enquiries", { maxBytes: 131072, enquiry: true });
}
