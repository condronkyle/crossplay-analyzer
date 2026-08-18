importScripts('quackle.js');

let modulePromise = null;

async function getModule() {
  if (!modulePromise) {
    modulePromise = (async () => {
      const module = await QuackleModule();
      if (!module.initEngine('/data')) throw new Error('Quackle engine initialization failed');
      return module;
    })();
  }
  return modulePromise;
}

self.addEventListener('message', async event => {
  const { id, type, payload = {} } = event.data || {};
  try {
    const module = await getModule();
    let result;

    if (type === 'init') {
      result = { info: module.getEngineInfo() };
    } else if (type === 'simulateKibitz') {
      result = module.simulateKibitz(
        payload.gridJson,
        payload.rack,
        payload.playerScore,
        payload.opponentScore,
        payload.numMoves,
        payload.iterations,
      );
    } else {
      throw new Error(`Unknown Quackle worker request: ${type}`);
    }

    self.postMessage({ id, result });
  } catch (error) {
    self.postMessage({
      id,
      error: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : '',
    });
  }
});
