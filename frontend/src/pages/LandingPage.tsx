import '@mantine/core/styles.css';

import {
  Container,
  Title,
  Text,
  Button,
  Group,
  Stack,
  Grid,
  Card,
  Badge,
  Box,
  Center,
  ThemeIcon,
  SimpleGrid,
} from '@mantine/core';
import {
  IconMusic,
  IconUsers,
  IconVersions,
  IconFileMusic,
  IconDownload,
  IconSettings,
  IconCloudUpload,
  IconDeviceDesktop,
  IconBrandGithub
} from '@tabler/icons-react';
import { Link } from 'react-router-dom';

export default function LandingPage() {
  const features = [
    {
      icon: IconMusic,
      title: "Standalone Part Formatter",
      description: "Automatically format and engrave your MuseScore files with professional-quality output. Perfect spacing, layout, and typography with zero manual work.",
      color: "blue"
    },
    {
      icon: IconUsers,
      title: "Ensemble Management",
      description: "Built specifically for large ensembles. Manage multiple musicians, distribute parts efficiently, and keep everyone synchronized.",
      color: "green"
    },
    {
      icon: IconVersions,
      title: "Version Tracking",
      description: "Never lose track of score revisions again. Complete version history with easy rollbacks and change tracking for collaborative workflows.",
      color: "violet"
    },
    {
      icon: IconFileMusic,
      title: "MuseScore Integration",
      description: "Seamless integration with MuseScore files. Import, process, and distribute your scores without leaving the platform.",
      color: "orange"
    }
  ];

  const benefits = [
    {
      icon: IconCloudUpload,
      title: "Cloud-Based",
      description: "Access your scores from anywhere, collaborate in real-time"
    },
    {
      icon: IconSettings,
      title: "Automated Processing",
      description: "Intelligent formatting that saves hours of manual work"
    },
    {
      icon: IconDeviceDesktop,
      title: "Professional Output",
      description: "Publication-ready engraving and layout"
    }
  ];

  return (
    <Box style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      {/* Hero Section */}
      <Container size="lg" py={80}>
        <Center>
          <Stack align="center">
            <ThemeIcon size={80} radius="xl" variant="light" color="white">
              <IconMusic size={40} />
            </ThemeIcon>
            
            <Title 
              c="white"
              order={1} 
              size={60}
              style={{ 
                textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
                lineHeight: 1.2
              }}
            >
              Divisi App
            </Title>
            
            <Text 
              c="white" 
              style={{ 
                textShadow: '1px 1px 2px rgba(0,0,0,0.3)',
                maxWidth: 600,
                opacity: 0.95
              }}
            >
              Score management software with intelligent part formatting
            </Text>
            
            <Group mt={20}>
              <Button 
                size="xl" 
                radius="xl" 
                variant="white"
                style={{
                  boxShadow: '0 8px 25px rgba(0,0,0,0.2)',
                  transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                }}
                component={Link}
                to="/app/ensembles"
              >
                Get Started Free
              </Button>
              <Button 
                size="xl" 
                radius="xl" 
                variant="outline" 
                color="white"
                style={{
                  borderColor: 'rgba(255,255,255,0.8)',
                  color: 'white'
                }}
                component={Link}
                to="/app"
              >
                Learn More
              </Button>
            </Group>
            
            <Badge 
              size="lg" 
              radius="xl" 
              variant="light" 
              color="white"
              style={{ 
                backgroundColor: 'rgba(255,255,255,0.2)',
                color: 'white',
                fontWeight: 500
              }}
            >
              🎵 Completely Free
            </Badge>
          </Stack>
        </Center>
      </Container>

      {/* Features Section */}
      <Box style={{ backgroundColor: 'white' }} py={80}>
        <Container size="lg">
          <Stack>
            <Center>
              <Stack align="center">
                <Title order={2} size={42} c="dark">
                  Everything you need for ensemble management
                </Title>
                <Text c="dimmed" style={{ maxWidth: 600 }}>
                  From automated part formatting to comprehensive version tracking, 
                  Divisi streamlines your entire musical workflow
                </Text>
              </Stack>
            </Center>

            <SimpleGrid 
              cols={2} 
              spacing={40}
            >
              {features.map((feature, index) => (
                <Card 
                  key={index} 
                  shadow="lg" 
                  radius="xl" 
                  padding={30}
                  style={{
                    border: '1px solid #f0f0f0',
                    transition: 'transform 0.3s ease, box-shadow 0.3s ease'
                  }}
                >
                  <Stack>
                    <ThemeIcon 
                      size={60} 
                      radius="xl" 
                      variant="light" 
                      color={feature.color}
                    >
                      <feature.icon size={30} />
                    </ThemeIcon>
                    
                    <Title order={3} size={24}>
                      {feature.title}
                    </Title>
                    
                    <Text c="dimmed" style={{ lineHeight: 1.6 }}>
                      {feature.description}
                    </Text>
                  </Stack>
                </Card>
              ))}
            </SimpleGrid>
          </Stack>
        </Container>
      </Box>

      {/* Standalone Formatter Highlight */}
      <Box style={{ backgroundColor: '#f8f9fa' }} py={80}>
        <Container size="lg">
          <Grid align="center" gutter={60}>
            <Grid.Col span={6}>
              <Stack>
                <Badge size="lg" radius="xl" color="blue" variant="light">
                  ⚡ Standalone Tool Available
                </Badge>
                
                <Title order={2} size={38}>
                  Professional Part Formatting
                </Title>
                
                <Text c="dimmed" style={{ lineHeight: 1.7 }}>
                  Our intelligent part formatter works independently or as part of the 
                  full ensemble system. Upload your MuseScore files and get 
                  professionally engraved parts in seconds.
                </Text>
                
                <Stack>
                  {benefits.map((benefit, index) => (
                    <Group key={index}>
                      <ThemeIcon size={40} radius="xl" color="blue" variant="light">
                        <benefit.icon size={20} />
                      </ThemeIcon>
                      <Box>
                        <Text>{benefit.title}</Text>
                        <Text size="sm" color="dimmed">{benefit.description}</Text>
                      </Box>
                    </Group>
                  ))}
                </Stack>
                
                <Button 
                  size="lg" 
                  radius="xl" 
                  style={{ alignSelf: 'flex-start' }}
                  component={Link}
                  to="/part-formatter"
                >
                  Try Formatter Now
                </Button>
              </Stack>
            </Grid.Col>
            
            <Grid.Col span={6}>
              <Box 
                style={{
                  height: 400,
                  backgroundColor: 'white',
                  borderRadius: 20,
                  boxShadow: '0 20px 40px rgba(0,0,0,0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid #e0e0e0'
                }}
              >
                <Stack align="center">
                  <ThemeIcon size={100} radius="xl" color="blue" variant="light">
                    <IconMusic size={50} />
                  </ThemeIcon>
                  <Text c="dimmed">
                    Pictures coming soon(tm)
                  </Text>
                </Stack>
              </Box>
            </Grid.Col>
          </Grid>
        </Container>
      </Box>

      {/* CTA Section */}
      <Box style={{ backgroundColor: '#1a1b23' }} py={80}>
        <Container size="lg">
          <Center>
            <Stack align="center">
              <Title order={2} size={36} c="white" style={{ maxWidth: 500 }}>
                Ready to revolutionize your ensemble workflow?
              </Title>
              
              <Text c="dimmed" style={{ maxWidth: 500 }}>
                Join musicians worldwide who trust Divisi for professional 
                score management and part formatting.
              </Text>
              
              <Group>
                <Button 
                  size="xl" 
                  radius="xl" 
                  variant="white"
                  style={{
                    boxShadow: '0 8px 25px rgba(0,0,0,0.3)'
                  }}
                  component={Link}
                  to="/app/ensembles"
                >
                  Start Using Divisi
                </Button>
                <Button 
                  size="xl" 
                  radius="xl" 
                  variant="outline" 
                  color="white"
                  component="a"
                  href="https://github.com/nbiancolin/SkuleNite-Divisi"
                  target="_blank"
                >
                  View on GitHub
                </Button>
              </Group>
              
              <Text size="sm" c="dimmed" mt={20}>
                🎼 Completely free • No account required for formatter • Open source
              </Text>
            </Stack>
          </Center>
        </Container>
      </Box>
    </Box>
  );
};

