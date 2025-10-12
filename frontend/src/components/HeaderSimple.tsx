import { useState, useEffect } from 'react';
import { Burger, Container, Group, Title, Alert } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import classes from './HeaderSimple.module.css';
import { Link } from 'react-router-dom';
import { apiService } from '../services/apiService';

const links = [
  { link: '/app', label: 'Ensemble Score Management' },
  { link: '/part-formatter', label: 'Part Formatter' },
  { link: '/contact', label: 'Contact' },
];

export function HeaderSimple() {
  const [opened, { toggle }] = useDisclosure(false);
  const [active, setActive] = useState(() => window.location.pathname);
  const [warnings, setWarnings] = useState([]);

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

  useEffect(() => {
    const fetchWarnings = async () => {
      try {
        const data = await apiService.getWarnings();
        setWarnings(data);
      } catch (error) {
        console.error('Failed to fetch warnings:', error);
      }
    };

    fetchWarnings();
    
    // Optional: Set up polling to check for new warnings every X seconds
    const interval = setInterval(fetchWarnings, 30000); // checks every 30 seconds
    
    return () => clearInterval(interval); // cleanup on unmount
  }, []);

return (
    <>
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
        {warnings.length > 0 && (
        <Container size="md" mb="lg" mt="xs">
          {warnings.map((warning, index) => (
            <Alert
              key={index}
              color="yellow"
              title="Warning"
              mb={index < warnings.length - 1 ? 'sm' : 0}
            >
              {warning}
            </Alert>
          ))}
        </Container>
      )}
      </header>
    </>
  );
}