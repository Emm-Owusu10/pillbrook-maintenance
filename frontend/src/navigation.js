// The links in the header that depend on who is signed in.
// An item without a "permission" is for any signed-in person. Later steps add items such as
// { to: "/requests", label: "All requests", permission: "view_all_requests" }.
export const NAV_ITEMS = [{ to: "/account", label: "My account" }];

export function visibleNavItems(items, { status, can }) {
  if (status !== "signedIn") return [];
  return items.filter((item) => !item.permission || can(item.permission));
}