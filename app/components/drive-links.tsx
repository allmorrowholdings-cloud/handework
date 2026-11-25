export type DriveLink = {
  id: string; title: string; url: string; kind: "file" | "folder" | "item";
  purpose: string; course_title?: string;
};

export type Submission = DriveLink & {
  status: string; version: number; review_note?: string; owner_name?: string;
};

export function DriveAnchor({ item }: { item: DriveLink }) {
  return <a className="text-link" href={item.url} target="_blank" rel="noopener noreferrer">
    {item.title} · Google Drive {item.kind}
  </a>;
}

export function DriveLinks({ items }: { items: DriveLink[] }) {
  return <div><ul>{items.map(item => <li key={item.id}>
    {item.course_title && <strong>{item.course_title} · </strong>}<DriveAnchor item={item}/>
  </li>)}</ul><small>Hosted on Google Drive. The owner controls access through Drive sharing settings.</small></div>;
}
