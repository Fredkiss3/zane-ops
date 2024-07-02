import { createFileRoute } from "@tanstack/react-router";
import { ChevronsUpDown, PlusIcon, Rocket, Search, Trash } from "lucide-react";
import { withAuthRedirect } from "~/components/helper/auth-redirect";
import { MetaTitle } from "~/components/meta-title";
import { DockerServiceCard, GitServiceCard } from "~/components/service-cards";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from "~/components/ui/breadcrumb";
import { Button } from "~/components/ui/button";

import { Input } from "~/components/ui/input";
import {
  Menubar,
  MenubarContent,
  MenubarContentItem,
  MenubarMenu,
  MenubarTrigger
} from "~/components/ui/menubar";
import { Separator } from "~/components/ui/separator";

export const Route = createFileRoute("/_dashboard/project/$slug")({
  component: withAuthRedirect(ProjectDetail)
});

function ProjectDetail() {
  const { slug } = Route.useParams();
  return (
    <main>
      <MetaTitle title="Project Detail" />
      <Breadcrumb>
        <BreadcrumbList className="text-sm">
          <BreadcrumbItem>
            <BreadcrumbLink href="/">Projects</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{slug}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center md:flex-nowrap lg:my-0 md:my-1 my-5 flex-wrap  gap-3 justify-between ">
        <div className="flex items-center gap-4 ">
          <h1 className="text-3xl capitalize font-medium">{slug}</h1>
          <Button className="flex gap-2">
            New Service <PlusIcon size={18} />
          </Button>
        </div>
        <div className="flex my-3 flex-wrap  w-full justify-end items-center md:gap-3 gap-1">
          <div className="flex md:my-5 lg:w-1/3 md:w-1/2 w-full items-center">
            <Search size={20} className="relative left-5" />
            <Input
              className="px-14 -mx-5 w-full my-1 text-sm focus-visible:right-0"
              placeholder="Ex: ZaneOps"
            />
          </div>
          <div className="md:w-fit w-full">
            <Menubar className="border border-border md:w-fit w-full">
              <MenubarMenu>
                <MenubarTrigger className="flex md:w-fit w-full ring-secondary md:justify-center justify-between text-sm items-center gap-1">
                  Status
                  <ChevronsUpDown className="w-4" />
                </MenubarTrigger>
                <MenubarContent className="border w-[calc(var(--radix-menubar-trigger-width)+0.5rem)] border-border md:min-w-6 md:w-auto">
                  <MenubarContentItem icon={Rocket} text="Active" />
                  <MenubarContentItem icon={Trash} text="Archived" />
                </MenubarContent>
              </MenubarMenu>
            </Menubar>
          </div>
        </div>
      </div>

      <h1 className="text-base font-semibold py-3">Services</h1>
      <Separator />
      <div className="py-8  grid lg:grid-cols-3 md:grid-cols-2 grid-cols-1 place-content-center  gap-8">
        <GitServiceCard
          name="api"
          branchName="main"
          repository="https://github.com/zaneops/zaneops/backend"
          status="healthy"
          updatedAt="yesterday"
          lastCommitMessage="fix: logs api #fbe5f7d"
          url="https://www.app.zaneops.dev/api/"
        />

        <GitServiceCard
          name="frontend"
          branchName="main"
          repository="https://github.com/zaneops/zaneops/frontend"
          status="healthy"
          updatedAt="yesterday"
          lastCommitMessage="fix: logs api #fbe5f7d"
          url="https://www.app.zaneops.dev/"
        />

        <GitServiceCard
          name="celery-worker"
          branchName="main"
          repository="https://github.com/zaneops/zaneops/backend"
          status="sleeping"
          updatedAt="yesterday"
          lastCommitMessage="fix: logs api #fbe5f7d"
          url="https://www.app.zaneops.dev/"
        />

        <DockerServiceCard
          name="redis"
          image="valkey/valkey"
          tag="latest"
          volumeNumber={1}
          status="healthy"
          updatedAt="2 months ago"
        />

        <DockerServiceCard
          name="database"
          image="postgres"
          tag="15:alpine"
          volumeNumber={0}
          status="healthy"
          updatedAt="2 months ago"
        />

        <DockerServiceCard
          name="proxy"
          image="ghcr.io/zaneops/proxy"
          tag="1.5.0"
          volumeNumber={1}
          url="https://www.ghcr.io/zaneops/proxy"
          status="healthy"
          updatedAt="2 months ago"
        />
      </div>

      <div className="col-span-3 flex justify-center mb-3 ">
        <Button
          variant="outline"
          className="lg:w-[50%] w-full border text-foreground p-6"
        >
          Load More
        </Button>
      </div>
    </main>
  );
}
