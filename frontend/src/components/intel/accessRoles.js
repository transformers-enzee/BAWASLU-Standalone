export const bawasluRoles = [
 'National Administrator',
 'National Leadership',
 'National Analyst',
 'Provincial Administrator',
 'Provincial Analyst',
 'Regency/City Officer',
 'Regency/City Analyst',
 'Viewer'
];
export const scopeForRole = role => role.startsWith('National ')?'Nationwide':role.startsWith('Provincial ')?'Province':role.startsWith('Regency/City ')?'Regency/City':'';
export const sensitivePermissions = ['human_validation','verify_evidence','manage_users'];