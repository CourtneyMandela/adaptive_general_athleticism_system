import { handleApiGateway } from "@/lib/api-gateway";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type GatewayContext = {
  params: Promise<{ path: string[] }>;
};

async function gateway(request: Request, context: GatewayContext): Promise<Response> {
  const { path } = await context.params;
  return handleApiGateway(request, path);
}

export const DELETE = gateway;
export const GET = gateway;
export const HEAD = gateway;
export const PATCH = gateway;
export const POST = gateway;
export const PUT = gateway;
