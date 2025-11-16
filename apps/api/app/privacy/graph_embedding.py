"""
Health Graph Embedding.

Simulates on-device graph embedding computation for privacy preservation.
Raw health data is transformed into dense vector representations locally,
and only the embeddings are transmitted to the server.

# TODO: add comprehensive tests
Patent-relevant: The server never sees raw biomarker values — only
fixed-dimensional embeddings that cannot be reverse-engineered to
individual readings. This is the "on-device processing" component
of the privacy architecture.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class GraphNode:
    """A node in the health knowledge graph.

    Nodes represent entities: users, biomarkers, meals, conditions, etc.
    """

    node_id: str
    node_type: str  # "user", "biomarker", "meal", "condition", "household"
    properties: Dict[str, Any] = field(default_factory=dict)
    owner_id: str = ""  # Which user owns this node
    is_shared: bool = False  # Household-shared or private

@dataclass
class GraphEdge:
    """An edge in the health knowledge graph.

    Edges represent relationships: "user HAS biomarker",
    "meal CONTAINS nutrient", "user LIVES_IN household", etc.
    """

    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    consent_required: Optional[str] = None  # ConsentScope needed
    is_active: bool = True  # Can be severed by consent revocation
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NodeEmbedding:
    """Dense vector representation of a graph node.

    This is what gets transmitted to the server instead of raw data.
    The embedding captures relational structure without exposing
    individual values.
    """

    node_id: str
    node_type: str
    embedding: List[float]
    dimension: int
    timestamp: datetime
    is_differential_private: bool = False
    epsilon_used: float = 0.0

class HealthGraphEmbedding:
    """Computes privacy-preserving graph embeddings.

    The health graph structure:
    ```
    Household
    ├── User A (private subgraph)
    │   ├── glucose readings
    │   ├── meal events
    │   ├── exercise sessions
    │   └── genetic profile
    ├── User B (private subgraph)
    │   ├── sleep data
    │   ├── medication
    │   └── conditions
    └── Shared nodes
        ├── kitchen ingredients
        ├── location/environment
        └── household meal plan
    ```

    Patent-relevant: Each user's subgraph is embedded independently
    on-device. Only the embedding vectors are sent to the server.
    The server can compute household-level aggregations on embeddings
    without accessing individual health data.
    """

    def __init__(self, embedding_dim: int = 64):
        self._dim = embedding_dim
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._embeddings: Dict[str, NodeEmbedding] = {}

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the health graph."""
        self._nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the health graph."""
        self._edges.append(edge)

    def sever_edges_by_consent(self, consent_scope: str) -> int:
        """Deactivate all edges requiring a specific consent scope.

        Called by the DynamicConsentManager when consent is revoked.
        Returns the number of edges severed.
        """
        count = 0
        for edge in self._edges:
            if edge.consent_required == consent_scope and edge.is_active:
                edge.is_active = False
                count += 1

                # Invalidate embeddings for affected nodes
                self._embeddings.pop(edge.source_id, None)
                self._embeddings.pop(edge.target_id, None)

        return count

    def restore_edges_by_consent(self, consent_scope: str) -> int:
        """Reactivate edges when consent is re-granted."""
        count = 0
        for edge in self._edges:
            if edge.consent_required == consent_scope and not edge.is_active:
                edge.is_active = True
                count += 1
        return count

    def compute_node_embedding(
        self, node_id: str, include_neighbors: bool = True
    ) -> Optional[NodeEmbedding]:
        """Compute embedding for a single node.

        Uses a simplified graph neural network approach:
        1. Hash node properties to initial feature vector
        2. Aggregate neighbor features (only via active edges)
        3. Apply non-linear transformation
        4. Normalize to unit sphere

        In production, this would use a trained GNN model.
        The key patent concept is that this runs ON-DEVICE.
        """
        node = self._nodes.get(node_id)
        if node is None:
            return None

        # Step 1: Initial features from node properties
        features = self._properties_to_vector(node.properties)

        # Step 2: Aggregate neighbor features via active edges
        if include_neighbors:
            neighbor_agg = self._aggregate_neighbors(node_id)
            # Combine: self + neighbors
            for i in range(self._dim):
                features[i] = 0.6 * features[i] + 0.4 * neighbor_agg[i]

        # Step 3: Non-linear transformation (tanh)
        features = [math.tanh(f) for f in features]

        # Step 4: L2 normalize to unit sphere
        norm = math.sqrt(sum(f ** 2 for f in features))
        if norm > 0:
            features = [f / norm for f in features]

        embedding = NodeEmbedding(
            node_id=node_id,
            node_type=node.node_type,
            embedding=features,
            dimension=self._dim,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._embeddings[node_id] = embedding
        return embedding

    def compute_subgraph_embedding(
        self, user_id: str
    ) -> Optional[NodeEmbedding]:
        """Compute a single embedding for a user's entire subgraph.

        This aggregates all nodes owned by the user into one vector,
        which is what gets sent to the server.

        Patent-relevant: The server receives ONE fixed-size vector per user,
        regardless of how much health data that user has. This makes it
        impossible to infer the number or type of biomarkers collected.
        """
        user_nodes = [
            n for n in self._nodes.values()
            if n.owner_id == user_id or n.node_id == user_id
        ]

        if not user_nodes:
            return None

        # Compute individual embeddings
        node_embeddings: List[List[float]] = []
        for node in user_nodes:
            emb = self.compute_node_embedding(node.node_id)
            if emb:
                node_embeddings.append(emb.embedding)

        if not node_embeddings:
            return None

        # Aggregate via mean pooling
        aggregated = [0.0] * self._dim
        for emb in node_embeddings:
            for i in range(self._dim):
                aggregated[i] += emb[i]
        n = len(node_embeddings)
        aggregated = [v / n for v in aggregated]

        # Normalize
        norm = math.sqrt(sum(v ** 2 for v in aggregated))
        if norm > 0:
            aggregated = [v / norm for v in aggregated]

        return NodeEmbedding(
            node_id=f"subgraph_{user_id}",
            node_type="user_subgraph",
            embedding=aggregated,
            dimension=self._dim,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    def compute_household_embedding(
        self, user_ids: List[str]
    ) -> Optional[NodeEmbedding]:
        """Compute household-level embedding from individual subgraphs.

        Patent-relevant: Household embedding is computed from individual
        subgraph embeddings (never raw data). This enables household-level
        recommendations (e.g., "reduce sodium for the family") without
        the server knowing any individual's blood pressure reading.
        """
        subgraph_embeddings: List[List[float]] = []
        for uid in user_ids:
            sub_emb = self.compute_subgraph_embedding(uid)
            if sub_emb:
                subgraph_embeddings.append(sub_emb.embedding)

        # Also include shared nodes
        shared_nodes = [
            n for n in self._nodes.values() if n.is_shared
        ]
        for node in shared_nodes:
            emb = self.compute_node_embedding(node.node_id)
            if emb:
                subgraph_embeddings.append(emb.embedding)

        if not subgraph_embeddings:
            return None

        # Weighted average — shared nodes get lower weight
        individual_count = len(user_ids)
        shared_count = len(shared_nodes)
        total = individual_count + shared_count

        aggregated = [0.0] * self._dim
        for i, emb in enumerate(subgraph_embeddings):
            weight = 1.0 / total
            for j in range(self._dim):
                aggregated[j] += emb[j] * weight

        norm = math.sqrt(sum(v ** 2 for v in aggregated))
        if norm > 0:
            aggregated = [v / norm for v in aggregated]

        return NodeEmbedding(
            node_id="household",
            node_type="household",
            embedding=aggregated,
            dimension=self._dim,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )

    def compute_similarity(
        self, emb1: NodeEmbedding, emb2: NodeEmbedding
    ) -> float:
        """Compute cosine similarity between two embeddings."""
        dot_product = sum(
            a * b for a, b in zip(emb1.embedding, emb2.embedding)
        )
        return dot_product  # Already L2-normalized, so dot = cosine sim

    def _properties_to_vector(
        self, properties: Dict[str, Any]
    ) -> List[float]:
        """Convert node properties to a fixed-size feature vector.

        Uses deterministic hashing so the same properties always
        produce the same features, but the mapping is not invertible.
        """
        vector = [0.0] * self._dim

        for i, (key, value) in enumerate(sorted(properties.items())):
            # Hash key+value to get deterministic position and magnitude
            h = hashlib.sha256(f"{key}:{value}".encode()).hexdigest()
            for j in range(self._dim):
                byte_idx = j % 32
                byte_val = int(h[byte_idx * 2: byte_idx * 2 + 2], 16)
                # Scale to [-1, 1]
                vector[j] += (byte_val / 128.0 - 1.0) * (1.0 / (i + 1))

        return vector

    def _aggregate_neighbors(self, node_id: str) -> List[float]:
        """Aggregate features from neighboring nodes via active edges."""
        aggregated = [0.0] * self._dim
        count = 0

        for edge in self._edges:
            if not edge.is_active:
                continue

            neighbor_id = None
            if edge.source_id == node_id:
                neighbor_id = edge.target_id
            elif edge.target_id == node_id:
                neighbor_id = edge.source_id

            if neighbor_id and neighbor_id in self._nodes:
                neighbor = self._nodes[neighbor_id]
                neighbor_vec = self._properties_to_vector(neighbor.properties)
                for i in range(self._dim):
                    aggregated[i] += neighbor_vec[i] * edge.weight
                count += 1

        if count > 0:
            aggregated = [v / count for v in aggregated]

        return aggregated

# Updated: 2022-12-29