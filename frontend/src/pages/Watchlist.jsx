import { Navigate } from 'react-router-dom';
/** Legacy Watchlist URL stays working; tracking now lives inside Social Listening. */
export default function Watchlist(){return <Navigate replace to="/social-listening?tab=watchlist"/>;}
