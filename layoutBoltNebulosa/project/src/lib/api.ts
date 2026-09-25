export type TagNode = {
  id: string;
  label: string;
  count: number;
  cluster: number;
};

export type TagLink = {
  source: string;
  target: string;
  value: number;
};

export type TagGraph = {
  nodes: TagNode[];
  links: TagLink[];
};

export type TagEntry = {
  id: number;
  text: string;
  likes: number;
};

export type RelatedTag = {
  name: string;
  weight: number;
};

export type TagDetail = {
  name: string;
  count: number;
  entries: TagEntry[];
  related: RelatedTag[];
};

export async function fetchGraph(): Promise<TagGraph> {
  const res = await fetch('/api/graph');
  if (!res.ok) throw new Error('Impossibile caricare la nebulosa dei tag');
  return res.json();
}

export async function fetchTagDetail(name: string): Promise<TagDetail> {
  const res = await fetch(`/api/tag/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`Tag "${name}" non trovato`);
  return res.json();
}
