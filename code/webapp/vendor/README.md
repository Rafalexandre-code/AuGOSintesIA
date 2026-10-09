# vendor — bibliotecas de terceiros embutidas no site

| Arquivo | Origem | Licença |
|---|---|---|
| `three.min.js` | three.js **r147**, `build/three.min.js` ([github.com/mrdoob/three.js](https://github.com/mrdoob/three.js/tree/r147)) | MIT (`LICENSE-three.txt`) |
| `OrbitControls.js` | three.js r147, `examples/js/controls/OrbitControls.js` | MIT |

A r147 é a última versão com o build UMD e os controles em `examples/js`, que funcionam como `<script>` comum (sem
módulos ES) dentro da página única gerada por `build_site.py --artifact`. Usados só pela aba Nanocompósito 3D
(`../nano3d.js`). `build_site.py` copia estes arquivos para `site/vendor/` e os embute na página única. Não edite: para
atualizar, baixe a mesma versão (ou outra com build UMD) e confira a aba no navegador.
