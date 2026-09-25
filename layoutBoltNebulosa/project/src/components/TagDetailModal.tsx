import { ArrowUpRight, Hash, X } from 'lucide-react';
import type { TagDetail } from '@/lib/api';

type Props = {
  tag: TagDetail | null;
  onClose: () => void;
  onSelectTag: (name: string) => void;
};

export default function TagDetailModal({ tag, onClose, onSelectTag }: Props) {
  if (!tag) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card detail-card" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close"><X size={18} /></button>
        <div className="detail-kind"><Hash size={15} /> Tag</div>
        <h2 className="detail-title">{tag.name}</h2>
        <div className="detail-meta">
          <div><span>Frammenti</span><strong>{tag.count}</strong></div>
          <div><span>Tag collegati</span><strong>{tag.related.length}</strong></div>
        </div>

        {tag.entries.length > 0 && (
          <div className="detail-entries">
            {tag.entries.map((entry) => (
              <p className="detail-entry" key={entry.id}>{entry.text}</p>
            ))}
          </div>
        )}

        {tag.related.length > 0 && (
          <div className="detail-connections">
            <p className="detail-conn-heading">Tag collegati</p>
            <div className="detail-conn-list">
              {tag.related.map((rel) => (
                <button key={rel.name} className="detail-conn-item" onClick={() => onSelectTag(rel.name)}>
                  <span className="detail-conn-dot" />
                  {rel.name}
                  <ArrowUpRight size={12} />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
