/** Approved Watchlist V2.2 canvas. The same-origin adapter uses the
 * existing registry, source evidence and officer role permissions.
 * No fictional candidate or post records are bundled with this screen.
 */
export default function Watchlist(){
 return <section aria-label="Watchlist V2.2" className="-mx-5 -my-5 md:-mx-9 md:-my-9 bg-[#edf2f4]">
  <iframe title="BAWASLU Candidate Watchlist V2.2" src="/ui-freeze/watchlist-v2_2.html"
   className="block w-full border-0 bg-[#edf2f4]"
   style={{height:'calc(100vh - 76px)',minHeight:640}}/>
 </section>;
}
