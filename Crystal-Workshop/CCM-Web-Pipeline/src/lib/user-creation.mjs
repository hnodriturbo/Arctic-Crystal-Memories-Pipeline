/** Purpose: Restrict account creation to the active named owner and validate repeated fields. */
export function canCreateUsers(user,ownerRoles){return Boolean(user?.id&&user.isActive&&user.email?.toLowerCase()==='hreidar@ccm.is'&&ownerRoles.includes(user.role));}
export function validateNewUser(input,roles){
 if(!input||typeof input!=='object')throw Error('INVALID');
 const email=typeof input.email==='string'?input.email.trim().toLowerCase():'';
 if(email.length>254||!/^\S+@\S+\.\S+$/.test(email))throw Error('EMAIL');
 if(email!==input.emailAgain?.trim().toLowerCase())throw Error('EMAIL_MATCH');
 if(typeof input.password!=='string'||!input.password||input.password.length>1024)throw Error('PASSWORD');
 if(input.password!==input.passwordAgain)throw Error('PASSWORD_MATCH');
 if(!roles.includes(input.role))throw Error('ROLE');
 if(email==='hreidar@ccm.is')throw Error('EXISTS');
 const name=typeof input.name==='string'?input.name.trim():'';if(name.length>120)throw Error('NAME');
 return {email,name:name||email.split('@')[0],role:input.role,password:input.password};
}
export function userCreationHandlers({actor,create,hash,roles,ownerRoles,origin}){return {
 async GET(){const user=await actor();return canCreateUsers(user,ownerRoles)?Response.json({canCreate:true,roles},{headers:{'Cache-Control':'no-store'}}):Response.json({canCreate:false},{status:user?403:401});},
 async POST(request){const user=await actor();if(!canCreateUsers(user,ownerRoles))return Response.json({error:'FORBIDDEN'},{status:user?403:401});if(request.headers.get('origin')!==origin(request))return Response.json({error:'ORIGIN'},{status:403});
 let input;try{const raw=await request.text();if(raw.length>16384)throw Error('INVALID');input=validateNewUser(JSON.parse(raw),roles);}catch(e){return Response.json({error:['EMAIL','EMAIL_MATCH','PASSWORD','PASSWORD_MATCH','ROLE','EXISTS','NAME'].includes(e.message)?e.message:'INVALID'},{status:400});}
 try{const {password,...data}=input;const result=await create({...data,passwordHash:await hash(password),isActive:true});return Response.json({ok:true,email:result.email,role:result.role},{status:201});}catch(e){return Response.json({error:e.code==='P2002'?'EXISTS':'FAILED'},{status:e.code==='P2002'?409:500});}
 }
};}
