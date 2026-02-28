"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { getGraph } from "@/lib/api";

interface GraphNode {
  id: string;
  name: string;
  domain: string;
  difficulty_tier: number;
  status: string;
  mastery_score: number;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  strength?: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const STATUS_COLORS: Record<string, string> = {
  mastered: "#22c55e",
  practicing: "#eab308",
  testing: "#eab308",
  introduced: "#60a5fa",
  decayed: "#f97316",
  unknown: "#6b7280",
};

function nodeRadius(tier: number) {
  return 8 + (tier || 1) * 4;
}

function nodeColor(status: string) {
  return STATUS_COLORS[status] || STATUS_COLORS.unknown;
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
      .then((res: any) => setData(res))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [learnerId]);

  const renderGraph = useCallback(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = containerRef.current.clientWidth;
    const height = 600;

    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const g = svg.append("g");

    // Zoom
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 5])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom);

    // Domain groups for subtle backgrounds
    const domains = Array.from(new Set(data.nodes.map((n) => n.domain)));
    const domainColor = d3.scaleOrdinal(d3.schemeTableau10).domain(domains);

    // Simulation
    const nodes = data.nodes.map((d) => ({ ...d }));
    const edges = data.edges.map((d) => ({ ...d }));

    const simulation = d3
      .forceSimulation(nodes as any)
      .force(
        "link",
        d3
          .forceLink(edges as any)
          .id((d: any) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d: any) => nodeRadius(d.difficulty_tier) + 4));

    // Draw edges
    const link = g
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d: any) => (d.type === "transfer" ? "#8b5cf6" : "#94a3b8"))
      .attr("stroke-width", 1.5)
      .attr("stroke-dasharray", (d: any) => (d.type === "transfer" ? "6 3" : "none"))
      .attr("stroke-opacity", (d: any) =>
        d.type === "transfer" ? (d.strength ?? 0.5) : 0.6
      );

    // Draw nodes
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

    // Domain halos
    node
      .append("circle")
      .attr("r", (d: any) => nodeRadius(d.difficulty_tier) + 6)
      .attr("fill", (d: any) => domainColor(d.domain))
      .attr("opacity", 0.15);

    // Main circles
    node
      .append("circle")
      .attr("r", (d: any) => nodeRadius(d.difficulty_tier))
      .attr("fill", (d: any) => nodeColor(d.status))
      .attr("stroke", "#fff")
      .attr("stroke-width", 2);

    // Labels
    node
      .append("text")
      .text((d: any) => d.name)
      .attr("dy", (d: any) => nodeRadius(d.difficulty_tier) + 14)
      .attr("text-anchor", "middle")
      .attr("fill", "#cbd5e1")
      .attr("font-size", 11)
      .attr("pointer-events", "none");

    // Hover
    node
      .on("mouseenter", (e, d: any) => {
        const rect = svgRef.current!.getBoundingClientRect();
        setTooltip({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top - 10,
          node: d,
        });
      })
      .on("mouseleave", () => setTooltip(null))
      .on("click", (_e, d: any) => {
        console.log("Node clicked:", d);
      });

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
      <div className="flex items-center justify-center h-[600px] bg-gray-900 rounded-lg">
        <p className="text-gray-400">Loading knowledge graph...</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[600px] bg-gray-900 rounded-lg">
        <div className="w-16 h-16 rounded-full bg-emerald-600/20 flex items-center justify-center mb-4">
          <span className="text-2xl text-emerald-400">P</span>
        </div>
        <h2 className="text-lg font-medium text-zinc-300 mb-2">Your knowledge map is empty</h2>
        <p className="text-zinc-500 max-w-md text-center mb-6">
          Start a learning session with your professor and your concepts will appear here as an interactive graph.
        </p>
        <a
          href="/session"
          className="inline-block px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-500 transition-colors text-sm font-medium"
        >
          Start learning
        </a>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full bg-gray-900 rounded-lg overflow-hidden">
      <svg ref={svgRef} className="w-full" style={{ height: 600 }} />

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
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <span key={status} className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
            {status}
          </span>
        ))}
      </div>
    </div>
  );
}
