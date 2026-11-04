export function interactionHasBlockingIssue(record) {
  if (record.beforeActions.authRedirected || record.beforeActions.unexpectedError) return true;
  if (record.apiIssues.some((issue) => issue.status === 401 || issue.status >= 500)) return true;
  return record.actions.some((action) => {
    if (action.status === "skipped-submit") return false;
    if (action.status !== "clicked") return true;
    if (action.stateAfterClick.authRedirected || action.stateAfterClick.unexpectedError) return true;
    if (action.stateAfterClose.authRedirected || action.stateAfterClose.unexpectedError) return true;
    return action.stateAfterClose.visibleDialogs > 0 && action.stateAfterClose.activeOverlays > 0;
  });
}

export function visualHasBlockingIssue(record) {
  return record.authRedirected || record.authApiIssues > 0 || record.serverApiIssues > 0
    || record.horizontalOverflow > 2 || record.transparentSurfaceIssues > 0;
}
