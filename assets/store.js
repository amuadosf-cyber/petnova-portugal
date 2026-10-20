'use strict';
// Apenas memória da página: sem checkout, armazenamento de dados pessoais ou rastreadores.
const euro = new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR'});
const cart = [];
let products = [];
let toastTimer;
const dialog = document.querySelector('#cart');
const symbols = {escovagem: '✧', brincadeira: '◉', refeicoes: '◒', passeio: '♧', casa: '≋'};
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderProducts(filter = 'Todos') {
  const grid = document.querySelector('#products');
  grid.replaceChildren();
  const filtered = products.filter(p => filter === 'Todos' || p.categoria.toLocaleLowerCase('pt-PT').includes(filter.toLocaleLowerCase('pt-PT')) || p.categoria === filter);
  for (const p of filtered) {
    const article = element('article', 'product');
    const art = element('div', 'product-art');
    art.setAttribute('aria-hidden', 'true');
    art.append(element('span', 'concept', 'ILUSTRAÇÃO DE CONCEITO'), element('span', 'product-symbol', symbols[p.tema] || '✧'));
    article.append(art, element('p', 'product-category', p.categoria), element('h3', '', p.nome), element('p', 'product-description', p.descricao));
    const bottom = element('div', 'product-bottom');
    const price = element('div', 'price', euro.format(Number(p.preco_demo_eur)));
    price.append(element('small', '', 'Preço ilustrativo'));
    const add = element('button', 'add', 'Experimentar no carrinho');
    add.type = 'button';
    add.setAttribute('aria-label', `Adicionar ${p.nome} ao carrinho de simulação`);
    add.addEventListener('click', () => {
      cart.push(p.id);
      renderCart();
      const toast = document.querySelector('#toast');
      toast.textContent = 'Adicionado ao carrinho de simulação.';
      toast.hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {toast.hidden = true;}, 2600);
    });
    bottom.append(price, add);
    article.append(bottom);
    grid.append(article);
  }
  document.querySelector('#catalog-status').textContent = `${filtered.length} produtos de demonstração apresentados.`;
}
function renderCart() {
  document.querySelector('#count').textContent = String(cart.length);
  const list = document.querySelector('#items');
  list.replaceChildren();
  let total = 0;
  if (!cart.length) list.append(element('li', '', 'O carrinho está vazio. Vamos explorar?'));
  for (const [index, id] of cart.entries()) {
    const product = products.find(p => p.id === id);
    total += Number(product.preco_demo_eur);
    const item = element('li');
    item.append(element('span', '', `${product.nome} · ${euro.format(Number(product.preco_demo_eur))}`));
    const remove = element('button', '', 'Remover');
    remove.setAttribute('aria-label', `Remover ${product.nome}`);
    remove.addEventListener('click', () => {cart.splice(index, 1); renderCart();});
    item.append(remove);
    list.append(item);
  }
  document.querySelector('#total').textContent = euro.format(total);
}
document.querySelector('#open-cart').addEventListener('click', () => {renderCart(); dialog.showModal();});
document.querySelector('#close-cart').addEventListener('click', () => {dialog.close();});
document.querySelector('#clear-cart').addEventListener('click', () => {cart.length = 0; renderCart();});
dialog.addEventListener('click', event => {if (event.target === dialog) {const r = dialog.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close();}});
for (const button of document.querySelectorAll('[data-filter]')) {
  button.addEventListener('click', () => {
    for (const other of document.querySelectorAll('[data-filter]')) other.setAttribute('aria-pressed', String(other === button));
    renderProducts(button.dataset.filter);
  });
}
async function init() {
  try {
    const response = await fetch('catalogo.json');
    if (!response.ok) throw new Error('Catálogo indisponível');
    const data = await response.json();
    if (data.mode !== 'demonstracao' || data.checkout_enabled !== false || !Array.isArray(data.products)) throw new Error('Modo de loja inválido');
    products = data.products;
    renderProducts();
    renderCart();
  } catch (_) {
    document.querySelector('#products').append(element('p', '', 'Não foi possível carregar o catálogo. Tenta atualizar a página. As compras continuam desativadas.'));
    document.querySelector('#catalog-status').textContent = 'Catálogo indisponível.';
  }
}
init();
