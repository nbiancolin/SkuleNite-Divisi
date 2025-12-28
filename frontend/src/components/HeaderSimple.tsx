import { useState, useEffect } from 'react';
import { Burger, Container, Group, Title, Alert, Button, Menu, Avatar, Text } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import classes from './HeaderSimple.module.css';
import { Link } from 'react-router-dom';
import { apiService, type User } from '../services/apiService';

const links = [
  { link: '/app', label: 'Ensemble Score Management' },
  { link: '/part-formatter', label: 'Part Formatter' },
  { link: '/contact', label: 'Contact' },
];

export function HeaderSimple() {
  const [opened, { toggle }] = useDisclosure(false);
  const [active, setActive] = useState(() => window.location.pathname);
  const [warnings, setWarnings] = useState([]);
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

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

    const fetchUser = async () => {
      try {
        const response = await apiService.getCurrentUser();
        setIsAuthenticated(response.is_authenticated);
        setUser(response.user);
      } catch (error) {
        console.error('Failed to fetch user:', error);
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    fetchWarnings();
    fetchUser();
    
    // Optional: Set up polling to check for new warnings every X seconds
    const interval = setInterval(fetchWarnings, 30000); // checks every 30 seconds
    
    return () => clearInterval(interval); // cleanup on unmount
  }, []);

  const handleLogin = () => {
    window.location.href = apiService.getDiscordLoginUrl();
  };

  const handleLogout = async () => {
    try {
      await apiService.logout();
      setIsAuthenticated(false);
      setUser(null);
      // Reload the page to clear any cached data
      window.location.reload();
    } catch (error) {
      console.error('Failed to logout:', error);
    }
  };

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
          <Group gap="sm">
            {!loading && (
              <>
                {isAuthenticated && user ? (
                  <Menu shadow="md" width={200}>
                    <Menu.Target>
                      <Button variant="subtle" style={{ padding: 0 }}>
                        <Group gap="xs">
                          {user.discord?.avatar ? (
                            <Avatar
                              src={`https://cdn.discordapp.com/avatars/${user.discord.id}/${user.discord.avatar}.png`}
                              size="sm"
                              radius="xl"
                            />
                          ) : (
                            <Avatar size="sm" radius="xl" color="blue">
                              {user.username.charAt(0).toUpperCase()}
                            </Avatar>
                          )}
                          <Text size="sm" fw={500}>
                            {user.discord?.username || user.username}
                          </Text>
                        </Group>
                      </Button>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Label>
                        <Text size="xs" c="dimmed">
                          {user.email}
                        </Text>
                      </Menu.Label>
                      <Menu.Divider />
                      <Menu.Item onClick={handleLogout} color="red">
                        Logout
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                ) : (
                  <Button onClick={handleLogin} variant="filled" color="blue">
                    Login with Discord
                  </Button>
                )}
              </>
            )}
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