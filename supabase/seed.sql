\ir ../src/data/seed_products.sql

insert into public.volume_promotions (name, minimum_kg, discount_percentage)
values
  ('Promo Vittamax', 60, 5),
  ('Promo Vittamax', 200, 5),
  ('Promo M-Line', 60, 2.5),
  ('Promo M-Line', 200, 5)
on conflict (name, minimum_kg) do update
set discount_percentage = excluded.discount_percentage;
