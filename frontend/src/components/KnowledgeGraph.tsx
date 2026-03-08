"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { getGraph, GraphNode, GraphData } from "@/lib/api";
import { GRAPH_STATUS_COLORS, GRAPH_EDGE_COLORS, GRAPH_CONFIG, ROUTES } from "@/lib/constants";

function nodeRadius(tier: number) {
  return GRAPH_CONFIG.NODE_BASE_RADIUS + (tier || 1) * GRAPH_CONFIG.NODE_TIER_SCALE;
}

function nodeColor(status: string) {
  return GRAPH_STATUS_COLORS[status] || GRAPH_STATUS_COLORS.unknown;
}

export default function KnowledgeGraph({ learnerId }: { learnerId?: string }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    node: GraphNode;
  } | null>(null);

  useEffect(() => {
    setLoading(true);
    getGraph(undefined, learnerId)
      .then((res) => setData(res))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [learnerId]);

  const renderGraph = useCallback(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = containerRef.current.clientWidth;
    const height = GRAPH_CONFIG.HEIGHT;

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const g = svg.append("g");

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([GRAPH_CONFIG.ZOOM_MIN, GRAPH_CONFIG.ZOOM_MAX])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    const domains = Array.from(new Set(data.nodes.map((n) => n.domain)));
    const domainColor = d3.scaleOrdinal(d3.schemeTableau10).domain(domains);

    const nodes = data.nodes.map((d) => ({ ...d }));
    const edges = data.edges.map((d) => ({ ...d }));

    const simulation = d3
      .forceSimulation(nodes as any)
      .force(
        "link",
        d3
          .forceLink(edges as any)
          .id((d: any) => d.id)
          .distance(GRAPH_CONFIG.LINK_DISTANCE)
      )
      .force("charge", d3.forceManyBody().strength(GRAPH_CONFIG.CHARGE_STRENGTH))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d: any) => nodeRadius(d.difficulty_tier) + GRAPH_CONFIG.COLLISION_PADDING));

    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d: any) => (d.type === "transfer" ? GRAPH_EDGE_COLORS.transfer : GRAPH_EDGE_COLORS.default))
      .attr("stroke-width", GRAPH_CONFIG.EDGE_STROKE_WIDTH)
      .attr("stroke-dasharray", (d: any) => (d.type === "transfer" ? GRAPH_CONFIG.EDGE_DASH_PATTERN : "none"))
      .attr("stroke-opacity", (d: any) =>
        d.type === "transfer" ? (d.strength ?? 0.5) : GRAPH_CONFIG.EDGE_DEFAULT_OPACITY
      );

    const node = g
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .call(
        d3
          .drag<SVGGElement, any>()
          .on("start", (e, d) => {
            if (!e.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (e, d) => {
            d.fx = e.x;
            d.fy = e.y;
          })
          .on("end", (e, d) => {
            if (!e.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          }) as any
      );

    node
      .append("circle")
      .attr("r", (d: any) => nodeRadius(d.difficulty_tier) + GRAPH_CONFIG.HALO_PADDING)
      .attr("fill", (d: any) => domainColor(d.domain))
      .attr("opacity", 0.15);

    node
      .append("circle")
      .attr("r", (d: any) => nodeRadius(d.difficulty_tier))
      .attr("fill", (d: any) => nodeColor(d.status))
      .attr("stroke", GRAPH_CONFIG.STROKE_COLOR)
      .attr("stroke-width", GRAPH_CONFIG.STROKE_WIDTH);

    node
      .append("text")
      .text((d: any) => d.name)
      .attr("dy", (d: any) => nodeRadius(d.difficulty_tier) + GRAPH_CONFIG.LABEL_OFFSET)
      .attr("text-anchor", "middle")
      .attr("fill", GRAPH_CONFIG.LABEL_COLOR)
      .attr("font-size", GRAPH_CONFIG.LABEL_FONT_SIZE)
      .attr("pointer-events", "none");

    node
      .on("mouseenter", (e, d: any) => {
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top - 10,
          node: d,
        });
      })
      .on("mouseleave", () => setTooltip(null));

    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data]);

  useEffect(() => {
    renderGraph();
  }, [renderGraph]);

  if (loading) {
    return (
      <div className="flex items-center justify-center bg-gray-900 rounded-lg" style={{ height: GRAPH_CONFIG.HEIGHT }}>
        <p className="text-gray-400">Loading knowledge graph...</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center bg-gray-900 rounded-lg" style={{ height: GRAPH_CONFIG.HEIGHT }}>
        <div className="w-16 h-16 rounded-full bg-emerald-600/20 flex items-center justify-center mb-4">
          <span className="text-2xl text-emerald-400">P</span>
        </div>
        <h2 className="text-lg font-medium text-zinc-300 mb-2">Your knowledge map is empty</h2>
        <p className="text-zinc-500 max-w-md text-center mb-6">
          Start a learning session with your professor and your concepts will appear here as an interactive graph.
        </p>
        <a
          href={ROUTES.SESSION}
          className="inline-block px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors text-sm font-medium"
        >
          Start learning
        </a>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full bg-gray-900 rounded-lg overflow-hidden">
      <svg ref={svgRef} className="w-full" style={{ height: GRAPH_CONFIG.HEIGHT }} />

      {tooltip && (
        <div
          className="absolute pointer-events-none bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm shadow-lg z-10"
          style={{ left: tooltip.x, top: tooltip.y, transform: "translate(-50%, -100%)" }}
        >
          <p className="font-semibold text-white">{tooltip.node.name}</p>
          <p className="text-gray-400">Domain: {tooltip.node.domain}</p>
          <p className="text-gray-400">
            Mastery: {((tooltip.node.mastery_score ?? 0) * 100).toFixed(0)}%
          </p>
        </div>
      )}

      <div className="absolute bottom-3 left-3 flex gap-3 text-xs text-gray-400">
        {Object.entries(GRAPH_STATUS_COLORS).map(([status, color]) => (
          <span key={status} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
            {status}
          </span>
        ))}
      </div>
    </div>
  );
}
