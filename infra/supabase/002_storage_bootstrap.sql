-- QCSpec storage bootstrap
-- Idempotent creation of required buckets and basic RLS policies.

-- 1) Required buckets
insert into storage.buckets (id, name, public)
values
  ('qcspec-photos', 'qcspec-photos', false),
  ('qcspec-reports', 'qcspec-reports', false),
  ('qcspec-templates', 'qcspec-templates', false)
on conflict (id) do update
set
  name = excluded.name,
  public = excluded.public;

-- 2) Optional baseline policies.
-- In hosted Supabase, this may require an owner role on storage.objects.
do $$
begin
  begin
    alter table storage.objects enable row level security;
  exception when insufficient_privilege then
    raise notice 'skip: no privilege to alter storage.objects';
  end;

  begin
    if not exists (
      select 1
      from pg_policies
      where schemaname = 'storage'
        and tablename = 'objects'
        and policyname = 'qcspec_objects_select'
    ) then
      create policy qcspec_objects_select
        on storage.objects
        for select
        to authenticated
        using (bucket_id in ('qcspec-photos', 'qcspec-reports', 'qcspec-templates'));
    end if;

    if not exists (
      select 1
      from pg_policies
      where schemaname = 'storage'
        and tablename = 'objects'
        and policyname = 'qcspec_objects_insert'
    ) then
      create policy qcspec_objects_insert
        on storage.objects
        for insert
        to authenticated
        with check (bucket_id in ('qcspec-photos', 'qcspec-reports', 'qcspec-templates'));
    end if;

    if not exists (
      select 1
      from pg_policies
      where schemaname = 'storage'
        and tablename = 'objects'
        and policyname = 'qcspec_objects_update'
    ) then
      create policy qcspec_objects_update
        on storage.objects
        for update
        to authenticated
        using (bucket_id in ('qcspec-photos', 'qcspec-reports', 'qcspec-templates'))
        with check (bucket_id in ('qcspec-photos', 'qcspec-reports', 'qcspec-templates'));
    end if;

    if not exists (
      select 1
      from pg_policies
      where schemaname = 'storage'
        and tablename = 'objects'
        and policyname = 'qcspec_objects_delete'
    ) then
      create policy qcspec_objects_delete
        on storage.objects
        for delete
        to authenticated
        using (bucket_id in ('qcspec-photos', 'qcspec-reports', 'qcspec-templates'));
    end if;
  exception when insufficient_privilege then
    raise notice 'skip: no privilege to create storage policies';
  end;
end $$;
