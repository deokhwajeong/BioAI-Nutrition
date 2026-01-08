"use client";

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface NeuralNetworkGraphProps {
  data: {
    input: string[];
    hidden: string[];
    output: string[];
  };
}

const NeuralNetworkGraph: React.FC<NeuralNetworkGraphProps> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous render

    const width = 600;
    const height = 400;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    svg.attr("width", width).attr("height", height);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Layer positions
    const layers = [
      { name: 'Input', nodes: data.input, x: innerWidth * 0.1 },
      { name: 'Hidden', nodes: data.hidden, x: innerWidth * 0.5 },
      { name: 'Output', nodes: data.output, x: innerWidth * 0.9 }
    ];

    // Calculate node positions
    layers.forEach(layer => {
      const nodeCount = layer.nodes.length;
      const ySpacing = innerHeight / (nodeCount + 1);
      layer.nodes.forEach((node, i) => {
        (layer as any).positions = (layer as any).positions || [];
        (layer as any).positions.push({
          x: layer.x,
          y: ySpacing * (i + 1),
          label: node
        });
      });
    });

    // Draw connections
    layers.slice(0, -1).forEach((layer, layerIndex) => {
      const nextLayer = layers[layerIndex + 1];
      (layer as any).positions.forEach((pos: any) => {
        (nextLayer as any).positions.forEach((nextPos: any) => {
          g.append("line")
            .attr("x1", pos.x)
            .attr("y1", pos.y)
            .attr("x2", nextPos.x)
            .attr("y2", nextPos.y)
            .attr("stroke", "#ccc")
            .attr("stroke-width", 1)
            .attr("opacity", 0.5);
        });
      });
    });

    // Draw nodes
    layers.forEach(layer => {
      (layer as any).positions.forEach((pos: any) => {
        const node = g.append("circle")
          .attr("cx", pos.x)
          .attr("cy", pos.y)
          .attr("r", 20)
          .attr("fill", "#4f46e5")
          .attr("stroke", "#fff")
          .attr("stroke-width", 2);

        // Add hover effect
        node.on("mouseover", function() {
          d3.select(this).attr("r", 25).attr("fill", "#7c3aed");
        }).on("mouseout", function() {
          d3.select(this).attr("r", 20).attr("fill", "#4f46e5");
        });

        // Add labels
        g.append("text")
          .attr("x", pos.x)
          .attr("y", pos.y + 5)
          .attr("text-anchor", "middle")
          .attr("font-size", "10px")
          .attr("fill", "#fff")
          .text(pos.label.length > 8 ? pos.label.substring(0, 8) + "..." : pos.label);
      });
    });

    // Add layer labels
    layers.forEach(layer => {
      g.append("text")
        .attr("x", layer.x)
        .attr("y", 15)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("font-weight", "bold")
        .attr("fill", "#374151")
        .text(layer.name);
    });

  }, [data]);

  return (
    <div className="w-full h-full flex items-center justify-center">
      <svg ref={svgRef} className="border rounded-lg shadow-sm"></svg>
    </div>
  );
};

export default NeuralNetworkGraph;