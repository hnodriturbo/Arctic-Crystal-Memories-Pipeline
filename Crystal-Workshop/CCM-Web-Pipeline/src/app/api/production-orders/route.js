/** Purpose: Authenticated order identity listing and order-scoped DXF version listing. */
import { operator, failure } from '@/lib/orders/access';
import { listOrders, getOrder, versions } from '@/lib/orders/storage.mjs';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export async function GET(request) {
  try {
    await operator(request);
    const key = new URL(request.url).searchParams.get('snapshot');
    const order = key ? await getOrder(key) : null;
    return Response.json(order ? { order, versions: await versions(order) } : { orders: await listOrders() }, { headers: { 'Cache-Control': 'private, no-store' } });
  } catch (error) { return failure(error); }
}
