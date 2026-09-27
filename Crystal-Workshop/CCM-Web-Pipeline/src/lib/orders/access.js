/** Purpose: Recheck active operator access for every private production order request. */
import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
export async function operator(request, write = false) {
  const session = await auth();
  if (!session?.user?.id) throw Error('ACCESS');
  const user = await prisma.user.findUnique({ where: { id: session.user.id }, select: { id: true, isActive: true, role: true } });
  if (!user?.isActive || user.role !== 'ADMIN') throw Error('ACCESS');
  if (write && request.headers.get('origin') !== new URL(process.env.AUTH_URL || request.url).origin) throw Error('ACCESS');
  return user;
}
export function failure(error) {
  console.error('[production-orders]', error.message === 'ACCESS' ? 'access denied' : error.name);
  return Response.json({ error: error.message === 'ACCESS' ? 'Access denied.' : 'Order storage could not be verified. Check configuration or retry.' }, { status: error.message === 'ACCESS' ? 403 : 422, headers: { 'Cache-Control': 'private, no-store' } });
}
