const LABELS = { admin: "Administrator", manager: "Facility Manager", user: "Farm User" };

export function roleLabel(role) {
  return LABELS[role] ?? "Unknown role";
}