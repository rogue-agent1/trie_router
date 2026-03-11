#!/usr/bin/env python3
"""HTTP URL router using radix trie — supports path params, wildcards, methods.

Like Express/Gin/Chi routers but from scratch.

Usage:
    python trie_router.py --test
"""

import sys


class RouteNode:
    __slots__ = ('children', 'param_child', 'wildcard_handler', 'handlers', 'param_name')

    def __init__(self):
        self.children = {}       # segment -> RouteNode
        self.param_child = None  # :param node
        self.param_name = None
        self.wildcard_handler = None  # * catch-all
        self.handlers = {}       # method -> handler


class Router:
    def __init__(self):
        self.root = RouteNode()

    def add(self, method: str, path: str, handler):
        """Register a route. Supports :param and * wildcard."""
        segments = [s for s in path.strip('/').split('/') if s]
        node = self.root

        for seg in segments:
            if seg.startswith(':'):
                if node.param_child is None:
                    node.param_child = RouteNode()
                    node.param_child.param_name = seg[1:]
                node = node.param_child
            elif seg == '*':
                node.wildcard_handler = (method, handler)
                return
            else:
                if seg not in node.children:
                    node.children[seg] = RouteNode()
                node = node.children[seg]

        node.handlers[method.upper()] = handler

    def match(self, method: str, path: str) -> tuple:
        """Match a request. Returns (handler, params) or (None, None)."""
        segments = [s for s in path.strip('/').split('/') if s]
        params = {}
        result = self._match(self.root, segments, 0, method.upper(), params)
        if result:
            return result, dict(params)
        return None, None

    def _match(self, node, segments, idx, method, params):
        if idx == len(segments):
            return node.handlers.get(method)

        seg = segments[idx]

        # Exact match first
        if seg in node.children:
            result = self._match(node.children[seg], segments, idx + 1, method, params)
            if result:
                return result

        # Param match
        if node.param_child:
            params[node.param_child.param_name] = seg
            result = self._match(node.param_child, segments, idx + 1, method, params)
            if result:
                return result
            del params[node.param_child.param_name]

        # Wildcard catch-all
        if node.wildcard_handler:
            m, h = node.wildcard_handler
            if m == method or m == '*':
                params['*'] = '/'.join(segments[idx:])
                return h

        return None

    def get(self, path, handler):
        self.add('GET', path, handler)

    def post(self, path, handler):
        self.add('POST', path, handler)

    def put(self, path, handler):
        self.add('PUT', path, handler)

    def delete(self, path, handler):
        self.add('DELETE', path, handler)


def test():
    print("=== Trie Router Tests ===\n")

    r = Router()
    r.get("/", "root")
    r.get("/users", "list_users")
    r.get("/users/:id", "get_user")
    r.post("/users", "create_user")
    r.get("/users/:id/posts/:post_id", "get_user_post")
    r.put("/users/:id", "update_user")
    r.get("/static/*", "serve_static")
    r.get("/api/v1/health", "health")

    # Exact match
    h, p = r.match("GET", "/")
    assert h == "root" and p == {}
    print("✓ Root route")

    h, p = r.match("GET", "/users")
    assert h == "list_users"
    print("✓ Static path")

    # Method differentiation
    h, p = r.match("POST", "/users")
    assert h == "create_user"
    print("✓ Method routing")

    # Params
    h, p = r.match("GET", "/users/42")
    assert h == "get_user" and p == {"id": "42"}
    print(f"✓ Path params: {p}")

    # Multiple params
    h, p = r.match("GET", "/users/42/posts/7")
    assert h == "get_user_post" and p == {"id": "42", "post_id": "7"}
    print(f"✓ Multiple params: {p}")

    # Wildcard
    h, p = r.match("GET", "/static/css/style.css")
    assert h == "serve_static" and p["*"] == "css/style.css"
    print(f"✓ Wildcard: {p}")

    # 404
    h, p = r.match("GET", "/nonexistent")
    assert h is None
    print("✓ 404 (no match)")

    # Wrong method
    h, p = r.match("DELETE", "/users")
    assert h is None
    print("✓ 405 (wrong method)")

    # Priority: exact > param
    h, p = r.match("GET", "/api/v1/health")
    assert h == "health"
    print("✓ Exact match priority over params")

    print("\nAll tests passed! ✓")


if __name__ == "__main__":
    test() if not sys.argv[1:] or sys.argv[1] == "--test" else None
