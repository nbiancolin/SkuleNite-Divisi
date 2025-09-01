import { useState } from 'react';
import { Burger, Container, Group, Title } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import classes from './HeaderSimple.module.css';
import { Link } from 'react-router-dom';

const links = [
  { link: '/app', label: 'Ensemble Score Management' },
  { link: '/part-formatter', label: 'Part Formatter' },
  { link: '/contact', label: 'Contact' },
];

export function HeaderSimple() {
  const [opened, { toggle }] = useDisclosure(false);
  const [active, setActive] = useState(() => window.location.pathname);

  const items = links.map((link) => (
    <a
      key={link.label}
      href={link.link}
      className={classes.link}
      data-active={active === link.link || undefined}
      onClick={() => {
        setActive(link.link);
      }}
    >
      {link.label}
    </a>
  ));

  return (
    <header className={classes.header}>
      <Container size="md" className={classes.inner}>
        <Link to="/" className={classes.titleLink}>
          <Title order={2}>Divisi App</Title>
        </Link>
        <Group gap={5} visibleFrom="xs">
          {items}
        </Group>

        <Burger opened={opened} onClick={toggle} hiddenFrom="xs" size="sm" />
      </Container>
    </header>
  );
}