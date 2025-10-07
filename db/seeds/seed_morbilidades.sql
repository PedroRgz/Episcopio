-- Seed data: Morbilidades comunes
INSERT INTO morbilidad (codigo, nombre, tipo) VALUES
('U07.1', 'COVID-19', 'transmisible'),
('A90', 'Dengue', 'transmisible'),
('A91', 'Dengue hemorrágico', 'transmisible'),
('J09', 'Influenza', 'transmisible'),
('A00', 'Cólera', 'transmisible'),
('A33', 'Tétanos neonatal', 'transmisible'),
('A37', 'Tos ferina', 'transmisible'),
('B05', 'Sarampión', 'transmisible'),
('B26', 'Parotiditis', 'transmisible'),
('B16', 'Hepatitis B', 'transmisible'),
('E10', 'Diabetes mellitus tipo 1', 'no_transmisible'),
('E11', 'Diabetes mellitus tipo 2', 'no_transmisible'),
('I10', 'Hipertensión esencial', 'no_transmisible'),
('I21', 'Infarto agudo de miocardio', 'no_transmisible'),
('C34', 'Cáncer de pulmón', 'no_transmisible')
ON CONFLICT (nombre) DO NOTHING;
