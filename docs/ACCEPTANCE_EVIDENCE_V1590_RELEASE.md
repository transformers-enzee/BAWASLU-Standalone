# v159.0 release validation

The v158.8 acceptance CSV frontend test originally asserted an exact release build label. Replace that with a minimum-version comparison so existing feature contract checks continue passing in later sequential releases. Combined with v158.9's active-admin fixture correction, the acceptance evidence export remains protected by standard Active + administration + view_intelligence permissions. No additional acceptance flags or approval paths were introduced.
