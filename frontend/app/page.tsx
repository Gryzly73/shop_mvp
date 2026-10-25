import { connection } from 'next/server';

export const dynamic = 'force-dynamic';

type Product = {
  id: string;
  title: string;
  image_url: string;
  created_at: string;
};

export default async function CatalogPage() {
  await connection();
  const backendUrl = process.env['BACKEND_INTERNAL_URL'];
  if (!backendUrl) {
    throw new Error('BACKEND_INTERNAL_URL is not set');
  }

  const response = await fetch(backendUrl + '/api/products', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load products: ${response.status}`);
  }
  const products = (await response.json()) as Product[];

  return (
    <main>
      <h1>Каталог</h1>
      <ul>
        {products.map((product) => (
          <li key={product.id}>
            <img src={product.image_url} alt={product.title} />
            {product.title}
          </li>
        ))}
      </ul>
    </main>
  );
}
