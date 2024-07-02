import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  ArrowDown,
  ArrowUp,
  ChevronsUpDown,
  Folder,
  Rocket,
  Search,
  Settings,
  Trash
} from "lucide-react";
import { withAuthRedirect } from "~/components/helper/auth-redirect";
import { MetaTitle } from "~/components/meta-title";
import { Input } from "~/components/ui/input";

import {
  Menubar,
  MenubarContent,
  MenubarContentItem,
  MenubarMenu,
  MenubarTrigger
} from "~/components/ui/menubar";

import { Loader } from "~/components/loader";
import { Pagination } from "~/components/pagination";
import { StatusBadge } from "~/components/status-badge";

import { useDebounce } from "use-debounce";
import { Button } from "~/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from "~/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from "~/components/ui/tooltip";
import { projectSearchSchema } from "~/key-factories";
import {
  useArchivedProjectList,
  useProjectList
} from "~/lib/hooks/use-project-list";
import { cn } from "~/lib/utils";
import { formattedDate } from "~/utils";

export const Route = createFileRoute("/_dashboard/")({
  validateSearch: (search) => projectSearchSchema.parse(search),
  component: withAuthRedirect(ProjectList)
});

export function ProjectList() {
  const {
    slug = "",
    page = 1,
    per_page = 10,
    sort_by = ["-updated_at"],
    status = "active"
  } = Route.useSearch();
  const [debouncedValue] = useDebounce(slug, 300);

  const navigate = useNavigate();

  const filters = {
    slug: debouncedValue,
    page,
    per_page,
    sort_by,
    status
  };

  const projectActiveQuery = useProjectList(filters);
  const projectArchivedQuery = useArchivedProjectList(filters);

  const query = status === "active" ? projectActiveQuery : projectArchivedQuery;

  if (query.isLoading) {
    return <Loader />;
  }

  const projectList = query.data?.data?.results ?? [];
  const totalProjects = query.data?.data?.count ?? 0;
  const totalPages = Math.ceil(totalProjects / per_page);

  const noResults = projectList.length === 0 && debouncedValue.trim() !== "";
  const empty = projectList.length === 0 && debouncedValue.trim() === "";

  const noActiveProjects = status === "active" && projectList.length === 0;

  const handleSort = (field: "slug" | "updated_at" | "archived_at") => {
    const isDescending = sort_by.includes(`-${field}`);
    const newSortBy = sort_by.filter(
      (criteria) => criteria !== field && criteria !== `-${field}`
    );
    newSortBy.push(isDescending ? field : `-${field}`);
    navigate({
      search: { ...filters, sort_by: newSortBy },
      replace: true
    });
  };

  const getArrowDirection = (field: "slug" | "updated_at" | "archived_at") => {
    if (sort_by.includes(`-${field}`)) {
      return "descending";
    }
    return "ascending";
  };
  const slugDirection = getArrowDirection("slug");
  const updatedAtDirection =
    status === "active"
      ? getArrowDirection("updated_at")
      : getArrowDirection("archived_at");

  return (
    <main>
      <MetaTitle title="Dashboard" />
      <section>
        <div className="md:my-10 my-5">
          <h1 className="text-3xl font-bold">Overview</h1>
          <h4 className="text-sm mt-2 opacity-60">List of projects</h4>
        </div>

        <div className="flex my-3 flex-wrap items-center md:gap-3 gap-1">
          <div className="flex md:my-5 md:w-[30%] w-full items-center">
            <Search size={20} className="relative left-5" />
            <Input
              onChange={(e) => {
                navigate({
                  search: {
                    ...filters,
                    slug: e.target.value,
                    page: 1
                  },
                  replace: true
                });
              }}
              defaultValue={slug}
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
                  <MenubarContentItem
                    onClick={() =>
                      navigate({
                        search: {
                          ...filters,
                          page: 1,
                          status: "active"
                        },
                        replace: true
                      })
                    }
                    icon={Rocket}
                    text="Active"
                  />

                  <MenubarContentItem
                    onClick={() =>
                      navigate({
                        search: {
                          ...filters,
                          page: 1,
                          status: "archived"
                        },
                        replace: true
                      })
                    }
                    icon={Trash}
                    text="Archived"
                  />
                </MenubarContent>
              </MenubarMenu>
            </Menubar>
          </div>
        </div>

        <Table>
          <TableHeader className="bg-toggle">
            <TableRow className="border-none">
              <TableHead>
                <TooltipProvider>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => handleSort("slug")}
                        className="flex cursor-pointer items-center gap-2"
                      >
                        Name
                        {slugDirection === "ascending" ? (
                          <ArrowDown size={15} />
                        ) : (
                          <ArrowUp size={15} />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="capitalize">{slugDirection}</div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </TableHead>
              <TableHead>Description</TableHead>
              <TableHead>
                <TooltipProvider>
                  <Tooltip delayDuration={0}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() =>
                          status === "active"
                            ? handleSort("updated_at")
                            : handleSort("archived_at")
                        }
                        className="flex cursor-pointer items-center gap-2"
                      >
                        {status === "active" ? "Last Updated" : "Archived At"}
                        {updatedAtDirection === "ascending" ? (
                          <ArrowDown size={15} />
                        ) : (
                          <ArrowUp size={15} />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <div className="capitalize">{updatedAtDirection}</div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </TableHead>
              <TableHead
                className={cn({
                  hidden: status === "archived"
                })}
              >
                Status
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {empty && noActiveProjects ? (
              <TableCell colSpan={5} className="text-center py-4">
                <section className="flex gap-3 flex-col items-center justify-center flex-grow py-20">
                  <div>
                    <h1 className="text-2xl font-bold">Welcome to ZaneOps</h1>
                    <h1 className="text-lg">You don't have any project yet</h1>
                  </div>
                  <Button asChild>
                    <Link to="/create-project">Create One</Link>
                  </Button>
                </section>
              </TableCell>
            ) : (
              ""
            )}

            {noResults ? (
              <TableRow className="border-border cursor-pointer">
                <TableCell colSpan={5} className="text-center py-4">
                  <h1 className="text-2xl font-bold">No results found</h1>
                </TableCell>
              </TableRow>
            ) : (
              projectList.map((project) => (
                <TableRow
                  className="border-border cursor-pointer"
                  key={project.id}
                >
                  <TableCell className="font-medium ">
                    <div className="flex gap-2">
                      <Folder size={18} />
                      {project.slug}
                    </div>
                  </TableCell>
                  <TableCell>{project.description}</TableCell>
                  {"updated_at" in project ? (
                    <TableCell>{formattedDate(project.updated_at)}</TableCell>
                  ) : (
                    <TableCell>{formattedDate(project.archived_at)}</TableCell>
                  )}

                  {"healthy_services" in project && (
                    <TableCell
                      className={cn({
                        hidden: status === "archived"
                      })}
                    >
                      <StatusBadge
                        color={
                          project.healthy_services === project.total_services
                            ? "green"
                            : project.healthy_services === 0
                              ? "red"
                              : "yellow"
                        }
                      >
                        <p>
                          {project.healthy_services}/
                          {`${project.total_services} Services Up`}
                        </p>
                      </StatusBadge>
                    </TableCell>
                  )}

                  <TableCell className="flex justify-end">
                    <div className="w-fit flex items-center gap-3">
                      Settings
                      <Settings width={18} />
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {!noResults && !empty && (
          <div
            className={cn("my-4 block", {
              "opacity-40 pointer-events-none": slug !== debouncedValue
            })}
          >
            <Pagination
              totalPages={totalPages}
              currentPage={page}
              perPage={per_page}
              onChangePage={(newPage) => {
                navigate({
                  search: { ...filters, page: newPage },
                  replace: true
                });
              }}
              onChangePerPage={(newPerPage) => {
                navigate({
                  search: {
                    ...filters,
                    page: 1,
                    per_page: newPerPage
                  },
                  replace: true
                });
              }}
            />
          </div>
        )}
      </section>
    </main>
  );
}
