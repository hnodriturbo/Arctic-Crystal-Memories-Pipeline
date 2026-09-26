/** Purpose: Recheck the named owner's database identity before creating any user. */
import argon2 from 'argon2';
import {prisma} from '@/lib/prisma';
import {userCreationHandlers} from '@/lib/user-creation.mjs';
import {auth} from '@/auth';
async function actor(){const session=await auth();if(!session?.user?.id)return null;return prisma.user.findUnique({where:{id:session.user.id},select:{id:true,email:true,role:true,isActive:true}});}
export const {GET,POST}=userCreationHandlers({actor,roles:["ADMIN"],ownerRoles:["OWNER"],hash:password=>argon2.hash(password,{type:argon2.argon2id}),create:data=>prisma.user.create({data,select:{email:true,role:true}}),origin:request=>new URL(process.env.AUTH_URL||process.env.NEXTAUTH_URL||request.url).origin});
