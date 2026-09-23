/**
 * Purpose: Rename the existing Workshop owner to CCM, preserving every other
 * account field. Apply requires a fresh pg_dump backup verified by pg_restore.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {PrismaClient} from '@prisma/client';
import {PrismaPg} from '@prisma/adapter-pg';
const apply=process.argv.includes('--apply');
const db=new PrismaClient({adapter:new PrismaPg({connectionString:process.env.DATABASE_URL})});
try{
 const rows=await db.user.findMany({where:{email:{in:['hreidar@acm.is','hreidar@ccm.is']}}});
 assert.equal(rows.length,1,'Expected exactly one existing owner; never merge accounts');
 const before=rows[0];assert.equal(before.role,'OWNER');assert.equal(before.isActive,true);
 if(apply&&before.email!=='hreidar@ccm.is'){
  const backupArg=process.argv.find(a=>a.startsWith('--backup-dir='));assert.ok(backupArg,'Explicit backup directory required');
  const folder=path.resolve(backupArg.slice(13));fs.mkdirSync(folder,{recursive:true,mode:0o700});
  const backup=path.join(folder,'workshop-before-ccm-email-23-09-2026-'+Date.now()+'.dump');
  const url=new URL(process.env.DATABASE_URL);
  const pgEnv={...process.env,PGHOST:url.hostname,PGPORT:url.port||'5432',PGUSER:decodeURIComponent(url.username),PGPASSWORD:decodeURIComponent(url.password),PGDATABASE:decodeURIComponent(url.pathname.slice(1))};
  const executable=name=>process.env.PG_BIN?path.join(process.env.PG_BIN,name+(process.platform==='win32'?'.exe':'')):name;
  execFileSync(executable('pg_dump'),['--format=custom','--no-owner','--no-acl','--file',backup],{env:pgEnv,stdio:['ignore','pipe','pipe']});
  assert.ok(fs.statSync(backup).size>0);const listing=execFileSync(executable('pg_restore'),['--list',backup],{encoding:'utf8'});assert.ok(listing.includes('TABLE DATA public users'));
  await db.$transaction(async tx=>{
   const current=await tx.user.findUnique({where:{id:before.id}});assert.deepEqual(current,before,'Owner changed since inspection');
   const after=await tx.user.update({where:{id:before.id},data:{email:'hreidar@ccm.is'}});
   const stable=({email,updatedAt,...rest})=>rest;assert.deepEqual(stable(after),stable(before));
  },{isolationLevel:'Serializable'});
  console.log(JSON.stringify({status:'renamed',id:before.id,email:'hreidar@ccm.is',passwordAndPermissionsPreserved:true,backup}));
 }else console.log(JSON.stringify({status:before.email==='hreidar@ccm.is'?'already-current':'dry-run',id:before.id,email:before.email}));
}finally{await db.$disconnect();}
