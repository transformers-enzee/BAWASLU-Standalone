/**
 * BAWASLU read-only Boolean matching for already saved social posts.
 * No provider query translation, regex evaluation, AI calls, or data writes.
 * AND binds more tightly than OR; NOT applies to the next word/group.
 */
const MAX_LENGTH=512;
const MAX_TOKENS=64;
const MAX_DEPTH=12;
const MAX_TERM_LENGTH=120;

export class BooleanSearchSyntaxError extends Error {
 constructor(message){super(message);this.name='BooleanSearchSyntaxError';}
}

function tokenize(input) {
 const tokens=[];
 for(let i=0;i<input.length;) {
  if(/\s/u.test(input[i])){i++;continue;}
  const char=input[i];
  if(char==='('||char===')'){tokens.push({type:char,value:char});i++;continue;}
  if(char==='"') {
   i++;let term='';let closed=false;
   while(i<input.length) {
    const ch=input[i++];
     if(ch==='\\'&&i<input.length&&(input[i]==='"'||input[i]==='\\')){term+=input[i++];continue;}
    if(ch==='"'){closed=true;break;}
    term+=ch;
   }
   if(!closed)throw new BooleanSearchSyntaxError('Close the quoted phrase with ".');
   if(!term.trim())throw new BooleanSearchSyntaxError('Quoted phrases cannot be empty.');
   if(term.length>MAX_TERM_LENGTH)throw new BooleanSearchSyntaxError('Each term must be 120 characters or fewer.');
   tokens.push({type:'TERM',value:term});
  }else{
   let term='';
   while(i<input.length&&!/\s/u.test(input[i])&&input[i]!=='('&&input[i]!==')'&&input[i]!=='"')term+=input[i++];
   if(!term)throw new BooleanSearchSyntaxError('Invalid Boolean search token.');
   if(term.length>MAX_TERM_LENGTH)throw new BooleanSearchSyntaxError('Each term must be 120 characters or fewer.');
   const type=['AND','OR','NOT'].includes(term.toUpperCase())?term.toUpperCase():'TERM';
   tokens.push({type,value:term});
  }
  if(tokens.length>MAX_TOKENS)throw new BooleanSearchSyntaxError('Use 64 words/operators or fewer.');
 }
 return tokens;
}

export function compileBooleanPostSearch(raw) {
 if(typeof raw!=='string'||!raw.trim())throw new BooleanSearchSyntaxError('Enter a Boolean search expression.');
 if(raw.length>MAX_LENGTH)throw new BooleanSearchSyntaxError('Boolean searches must be 512 characters or fewer.');
 const tokens=tokenize(raw.trim());
 let pos=0;
 const current=()=>tokens[pos];
 const consume=type=>{if(current()?.type===type){pos++;return true;}return false;};
 const requireToken=(type,message)=>{
  if(!consume(type))throw new BooleanSearchSyntaxError(message);
 };
 function or(depth){
  let node=and(depth);
  while(consume('OR'))node={type:'OR',left:node,right:and(depth)};
  return node;
 }
 function and(depth){
  let node=unary(depth);
  // "A NOT B" is shorthand for "A AND NOT B".
  while(current()?.type==='AND'||current()?.type==='NOT'){
   if(current()?.type==='AND')pos++;
   node={type:'AND',left:node,right:unary(depth)};
  }
  return node;
 }
 function unary(depth){
  if(depth>MAX_DEPTH)throw new BooleanSearchSyntaxError('Too many nested groups (maximum 12).');
  if(consume('NOT'))return {type:'NOT',child:unary(depth+1)};
  if(consume('(')){
   const node=or(depth+1);
   requireToken(')','Close each ( group with ).');
   return node;
  }
  if(current()?.type==='TERM'){
   const value=tokens[pos++].value.toLocaleLowerCase('id-ID');
   return {type:'TERM',value};
  }
  throw new BooleanSearchSyntaxError('Expected a word, quoted phrase, NOT, or ( group ).');
 }
 const ast=or(0);
 if(pos!==tokens.length)throw new BooleanSearchSyntaxError(
  'Add AND or OR between terms and check the parentheses.');
 function retrievalAnchors(node) {
  if(node.type==='TERM')return [node.value];
  if(node.type==='NOT')return null;
  const left=retrievalAnchors(node.left),right=retrievalAnchors(node.right);
  if(node.type==='OR')return left&&right?[...new Set([...left,...right])]:null;
  if(!left)return right;
  if(!right)return left;
  return left.length<=right.length?left:right;
 }
 function matches(node,text) {
  if(node.type==='TERM'){
   const term=node.value.trim().replace(/\s+/gu,' ');
   if(!term)return false;
   const isWord=c=>Boolean(c&&/[\p{L}\p{N}_]/u.test(c));
   let at=text.indexOf(term);
   while(at>=0){
    if((!isWord(term[0])||!isWord(text[at-1]))&&(!isWord(term[term.length-1])||!isWord(text[at+term.length])))return true;
    at=text.indexOf(term,at+1);
   }
   return false;
  }
  if(node.type==='NOT')return !matches(node.child,text);
  if(node.type==='AND')return matches(node.left,text)&&matches(node.right,text);
  return matches(node.left,text)||matches(node.right,text);
 }
 const predicate=post=>matches(ast,String(post?.text_content||'').toLocaleLowerCase('id-ID').trim().replace(/\s+/gu,' '));
 predicate.retrievalTerms=retrievalAnchors(ast);
 return predicate;
}

/** Validate a project query using the same provider-retrieval safeguards as the backend. */
export function compileBooleanProjectSearch(raw) {
 const predicate=compileBooleanPostSearch(raw);
 const anchors=predicate.retrievalTerms;
 if(!anchors?.length)throw new BooleanSearchSyntaxError(
  'A monitoring project needs a positive search term in every OR branch.');
 if(anchors.length>5)throw new BooleanSearchSyntaxError(
  'Use at most five independent positive search alternatives for collection.');
 return predicate;
}
