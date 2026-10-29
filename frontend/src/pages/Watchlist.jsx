import { Navigate } from 'react-router-dom';
/** The former standalone Watchlist URL now opens the campaign selector. */
export default function Watchlist(){return <Navigate replace to="/social-listening"/>;}
