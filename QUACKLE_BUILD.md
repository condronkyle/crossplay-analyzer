# Quackle WebAssembly provenance

The checked-in Quackle artifacts were built from
`condronkyle/quackle@0facea4` with:

```sh
./wasm/build.sh
```

The build used the optional `nwl23.gaddag` documented in the source
repository. Artifact SHA-256 values:

```text
quackle.js    26aa3381cfc560fc47e66ef06af71f6fbb994c0dbc995e321dfaf4d542f674d3
quackle.wasm  7ec9a20f1dcd787fb37104d08fc0c03e6043d6ebaaebad1bad3a7996a9881a0c
quackle.data  0f7b4e8cdcf4cb743c5423d6befe23ea77691c588f7c7dfb603bf475c1fbf8f3
```

The worker passes the observed bag count and explicit empty-bag final-turn
state to the engine. The engine rejects positions that do not conserve the
100 physical Crossplay tiles.
