-- Tabela de categorias
CREATE TABLE IF NOT EXISTS categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL
);

-- Seed categorias
INSERT INTO categorias (nome)
VALUES 
('Bebidas'),
('Alimentos'),
('Higiene')
ON CONFLICT (nome) DO NOTHING;

-- Tabela de produtos
CREATE TABLE IF NOT EXISTS produtos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    preco NUMERIC(10,2) NOT NULL,
    categoria_id INT REFERENCES categorias(id),
    estoque INT DEFAULT 0
);

-- Seed produtos
INSERT INTO produtos (nome, preco, categoria_id, estoque)
VALUES
('Água Mineral', 2.50, 1, 100),
('Refrigerante 2L', 7.50, 1, 50),
('Arroz 5kg', 25.00, 2, 30),
('Sabonete', 3.00, 3, 200)
ON CONFLICT (nome) DO NOTHING;
