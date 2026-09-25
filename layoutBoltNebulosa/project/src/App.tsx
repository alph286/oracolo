import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { ArrowUpRight, CircleHelp, Command, Search, X } from 'lucide-react';
import { fetchGraph, fetchTagDetail, type TagDetail, type TagGraph } from '@/lib/api';
import TagDetailModal from '@/components/TagDetailModal';
import miaIcona from './mistakelogo.png';

type GraphNode = {
  id: string;
  label: string;
  count: number;
  cluster: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  value: number;
};

const clusterColors = ['#FFB5E8', '#B5DEFF', '#E2C2FF', '#FFDAC1', '#FFF5BA', '#B5EAD7'];

const emptyGraph: TagGraph = { nodes: [], links: [] };

export default function App() {
  const [graphData, setGraphData] = useState<TagGraph>(emptyGraph);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showIntro, setShowIntro] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);
  const [detailTag, setDetailTag] = useState<TagDetail | null>(null);

  const graphRef = useRef<{ centerAt: (x: number, y: number, ms?: number) => void; zoom: (z: number, ms?: number) => void } | undefined>(undefined);

  // ── Load the tag graph from Oracolo ──
  const loadGraph = useCallback(async () => {
    try {
      const data = await fetchGraph();
      setGraphData(data);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Impossibile caricare la nebulosa');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const graph = useMemo<{ nodes: GraphNode[]; links: GraphLink[] }>(() => ({
    nodes: graphData.nodes.map((n) => ({ ...n })),
    links: graphData.links.map((l) => ({ ...l })),
  }), [graphData]);

  // ── Search: highlight tags matching the query and focus the first match ──
  const submitSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const term = searchTerm.trim().toLowerCase();
    if (!term) {
      setHighlightedIds([]);
      return;
    }
    const matches = graph.nodes.filter((n) => n.label.toLowerCase().includes(term));
    setHighlightedIds(matches.map((n) => n.id));
    const first = matches[0];
    if (first && typeof first.x === 'number' && typeof first.y === 'number' && graphRef.current) {
      graphRef.current.centerAt(first.x, first.y, 600);
      graphRef.current.zoom(3, 600);
    }
  };

  // ── Open detail panel for a tag ──
  const openTagDetail = useCallback(async (tagName: string) => {
    try {
      const detail = await fetchTagDetail(tagName);
      setDetailTag(detail);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Impossibile caricare il tag');
    }
  }, []);

  const handleNodeClick = (node: GraphNode) => {
    openTagDetail(node.id);
  };

  const isNearHovered = (node: GraphNode) => {
    if (!hoveredNode || !node.x || !node.y || !hoveredNode.x || !hoveredNode.y) return false;
    return Math.hypot(node.x - hoveredNode.x, node.y - hoveredNode.y) < 120;
  };

  if (loading || showIntro) {
    return (
      <main
        className="oracle-shell"
        style={{ cursor: loading ? 'wait' : 'pointer' }}
        onClick={() => {
          if (!loading) {
            setShowIntro(false);
          }
        }}
      >
        <div className="loading-screen flex flex-col items-center justify-center text-center px-6">
          <div className="loading-orb" />
          <p className="max-w-2xl mt-6" style={{ fontSize: '13px', lineHeight: '1.6' }}>
            L'Oracolo è una mente collettiva open source che si dirama in mille frammenti incandescenti. È uno strumento, un archivio, un ambiente generativo, un agglomeratore di pensieri, testi, file, fonti e prende la forma di ciò da cui è composto. È una nebulosa mutaforma messa a disposizione del Viandante, che è uno stato d'animo: è il divergente, il ricercatore, l'esploratore; quello che si fa domande.
          </p>

          {!loading && (
            <p className="pt-12 text-sm text-[#F3C58B] animate-pulse">
              [ ADDENTRATI NELLA NEBULOSA ]
            </p>
          )}
        </div>
      </main>
    );
  }

  return (
    <main className="oracle-shell">
      <div className="aurora aurora-one" />
      <div className="aurora aurora-two" />
      <div className="star-field" />
      <div className="graph-layer">
        <ForceGraph2D
          ref={graphRef as never}
          graphData={graph}
          backgroundColor="rgba(0,0,0,0)"
          nodeRelSize={4}
          d3AlphaDecay={0.018}
          d3VelocityDecay={0.32}
          linkColor={() => 'rgba(196, 177, 158, 0.14)'}
          linkWidth={(link: GraphLink) => {
            const source = typeof link.source === 'string' ? link.source : link.source.id;
            const target = typeof link.target === 'string' ? link.target : link.target.id;
            return highlightedIds.includes(source) || highlightedIds.includes(target) ? 0.8 : 0.35;
          }}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={1.2}
          linkDirectionalParticleSpeed={0.002}
          nodeColor={(node: GraphNode) => highlightedIds.includes(node.id) ? '#f3c58b' : clusterColors[node.cluster % clusterColors.length]}
          nodeVal={(node: GraphNode) => highlightedIds.includes(node.id) ? 11 : isNearHovered(node) ? 7 : 3.5}
          onNodeHover={(node: GraphNode | null) => setHoveredNode(node)}
          onNodeClick={handleNodeClick}
          nodeCanvasObject={(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
            const active = highlightedIds.includes(node.id);
            const nearby = isNearHovered(node);
            const base = 1.8 + Math.min(node.count, 8) * 0.35;
            const radius = (active ? base * 2.6 : nearby ? base * 1.8 : base) / Math.sqrt(globalScale);
            if (active || nearby) {
              const glow = ctx.createRadialGradient(node.x ?? 0, node.y ?? 0, 0, node.x ?? 0, node.y ?? 0, radius * 5);
              glow.addColorStop(0, active ? 'rgba(243,197,139,0.7)' : 'rgba(210,193,174,0.35)');
              glow.addColorStop(1, 'rgba(210,193,174,0)');
              ctx.fillStyle = glow;
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, radius * 5, 0, 2 * Math.PI, false);
              ctx.fill();
            }
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = active ? '#fff0d0' : clusterColors[node.cluster % clusterColors.length];
            ctx.fill();
            if (active) {
              ctx.strokeStyle = 'rgba(255, 223, 172, 0.7)';
              ctx.lineWidth = 1.2 / Math.sqrt(globalScale);
              ctx.stroke();
            }
          }}
          nodePointerAreaPaint={(node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, 10, 0, 2 * Math.PI, false);
            ctx.fill();
          }}
        />
      </div>

      <header className="topbar">
        <div className="brand-lockup">
          <img src={miaIcona} alt="Icona Nebulosa" className="w-9 h-10" />
          <div>
            <p className="eyebrow">Oracolo</p>
            <h1>LA NEBULOSA</h1>
          </div>
        </div>
        <div className="header-center"><span className="status-dot" />Frammento <span className="header-divider" /> {graphData.nodes.length} tag condivisi</div>
        <div className="header-actions">
          <button className="help-button" type="button" aria-label="Help"><CircleHelp size={17} strokeWidth={1.5} /></button>
        </div>
      </header>

      <aside className="side-panel left-panel">
        <p className="field-title">Un archivio di <br /><em>memorie collettive.</em></p>
        <p className="field-copy">Ogni tag nasce da un pensiero condiviso e si lega agli altri che ne condividono il tema. Esplora la nebulosa per scoprire come si intrecciano.</p>
        <div className="rule" />
        <div className="metric-grid">
          <div><strong>{graphData.nodes.length}</strong><span>tag</span></div>
          <div><strong>{graphData.links.length}</strong><span>connessioni</span></div>
        </div>
      </aside>

      <form className="oracle-input-wrap" onSubmit={submitSearch}>
        <div className="input-icon"><Search size={17} strokeWidth={1.5} /></div>
        <input
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Cerca un tag nella Nebulosa."
          aria-label="Cerca un tag"
        />
        <div className="input-hint"><Command size={12} /> <span>Invio</span></div>
        <button type="submit" aria-label="Cerca"><ArrowUpRight size={18} /></button>
      </form>

      {loadError && (
        <div className="error-toast">
          <span>{loadError}</span>
          <button onClick={() => setLoadError(null)}><X size={14} /></button>
        </div>
      )}

      <TagDetailModal
        tag={detailTag}
        onClose={() => setDetailTag(null)}
        onSelectTag={(name) => openTagDetail(name)}
      />
    </main>
  );
}
