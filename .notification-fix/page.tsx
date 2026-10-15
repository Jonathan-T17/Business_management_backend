"use client";

import {
  useMemo,
  useState,
} from "react";

import {
  useRouter,
} from "next/navigation";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  Bell,
  BellOff,
  CheckCheck,
  MailOpen,
  Search,
  Trash2,
} from "lucide-react";

import {
  deleteNotification,
  getNotifications,
  markAllAsRead,
  markAsRead,
  markAsUnread,
} from "@/api/notificationsApi";

import PageHeader from "@/components/ui/PageHeader";

import {
  notificationHref,
} from "@/utils/notifications";

import type {
  Notification,
} from "@/types/notification";


type NotificationFilter =
  | "all"
  | "unread"
  | "read";


export default function NotificationsPage() {
  const queryClient =
    useQueryClient();

  const router = useRouter();

  const [search, setSearch] =
    useState("");

  const [filter, setFilter] =
    useState<NotificationFilter>(
      "all"
    );


  const {
    data: notifications = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
  });


  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["notifications"],
      }),

      queryClient.invalidateQueries({
        queryKey: [
          "notifications",
          "unread-count",
        ],
      }),
    ]);
  }


  const readMutation =
    useMutation({
      mutationFn: markAsRead,
      onSuccess: refresh,
    });


  const unreadMutation =
    useMutation({
      mutationFn: markAsUnread,
      onSuccess: refresh,
    });


  const deleteMutation =
    useMutation({
      mutationFn:
        deleteNotification,

      onSuccess: refresh,
    });


  const readAllMutation =
    useMutation({
      mutationFn:
        markAllAsRead,

      onSuccess: refresh,
    });


  const filtered =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      return notifications.filter(
        (notification) => {
          if (
            filter === "unread" &&
            notification.is_read
          ) {
            return false;
          }

          if (
            filter === "read" &&
            !notification.is_read
          ) {
            return false;
          }

          if (!query) {
            return true;
          }

          return (
            notification.title
              .toLowerCase()
              .includes(query) ||
            notification.message
              .toLowerCase()
              .includes(query) ||
            notification.notification_type
              .toLowerCase()
              .includes(query)
          );
        }
      );
    }, [
      notifications,
      search,
      filter,
    ]);


  const unreadCount =
    notifications.filter(
      (notification) =>
        !notification.is_read
    ).length;


  async function openNotification(
    notification: Notification
  ) {
    if (!notification.is_read) {
      try {
        await markAsRead(
          notification.id
        );

        await refresh();
      } catch {
        // Navigation should still work.
      }
    }

    const href =
      notificationHref(
        notification
      );

    if (href) {
      router.push(href);
    }
  }


  return (
    <div className="space-y-7">

      <PageHeader
        title="Notifications"
        description="Follow updates about your work, reviews, invitations and account. Open an update to see its details."
        action={
          unreadCount > 0 ? (
            <button
              type="button"
              disabled={
                readAllMutation.isPending
              }
              onClick={() =>
                readAllMutation.mutate()
              }
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              <CheckCheck
                size={17}
              />

              Mark all read
            </button>
          ) : undefined
        }
      />


      <div className="grid gap-4 sm:grid-cols-3">

        <SummaryCard
          label="Total"
          value={
            notifications.length
          }
        />

        <SummaryCard
          label="Unread"
          value={unreadCount}
        />

        <SummaryCard
          label="Read"
          value={
            notifications.length -
            unreadCount
          }
        />
      </div>


      <div className="flex flex-col gap-3 md:flex-row">

        <div className="relative flex-1">
          <Search
            size={17}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />

          <input
            value={search}
            onChange={(event) =>
              setSearch(
                event.target.value
              )
            }
            placeholder="Search notifications..."
            className="w-full rounded-lg border border-gray-300 py-2.5 pl-9 pr-3 text-sm outline-none focus:border-blue-500"
          />
        </div>


        <select
          value={filter}
          onChange={(event) =>
            setFilter(
              event.target
                .value as NotificationFilter
            )
          }
          className="rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-700"
        >
          <option value="all">
            All
          </option>

          <option value="unread">
            Unread
          </option>

          <option value="read">
            Read
          </option>
        </select>
      </div>


      {isLoading ? (
        <NotificationLoading />
      ) : isError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">
          Unable to load notifications.
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">

          <BellOff
            size={38}
            className="mx-auto text-gray-400"
          />

          <h2 className="mt-4 font-semibold text-gray-900">
            No notifications
          </h2>

          <p className="mt-1 text-sm text-gray-500">
            There is nothing matching your current filter.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">

          <div className="divide-y divide-gray-100">

            {filtered.map(
              (notification) => (
                <NotificationRow
                  key={
                    notification.id
                  }
                  notification={
                    notification
                  }
                  onOpen={() =>
                    openNotification(
                      notification
                    )
                  }
                  onRead={() =>
                    readMutation.mutate(notification.id)
                  }
                  onUnread={() =>
                    unreadMutation.mutate(
                      notification.id
                    )
                  }
                  onDelete={() =>
                    deleteMutation.mutate(
                      notification.id
                    )
                  }
                />
              )
            )}
          </div>
        </div>
      )}
    </div>
  );
}


function NotificationRow({
  notification,
  onOpen,
  onRead,
  onUnread,
  onDelete,
}: {
  notification: Notification;
  onOpen: () => void;
  onRead: () => void;
  onUnread: () => void;
  onDelete: () => void;
}) {
  return (
    <article
      className={`relative p-5 transition ${
        notification.is_read
          ? "bg-[var(--surface)]"
          : "bg-[var(--accent-soft)]"
      }`}
    >
      {!notification.is_read && (
        <div className="absolute bottom-0 left-0 top-0 w-1 bg-[var(--accent)]" />
      )}


      <div className="flex gap-4">

        <button
          type="button"
          onClick={onOpen}
          className="flex min-w-0 flex-1 gap-4 text-left"
        >
          <div
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
              notification.is_read
                ? "bg-[var(--surface-soft)] text-[var(--muted)]"
                : "bg-[var(--surface)] text-[var(--accent-text)]"
            }`}
          >
            <Bell size={18} />
          </div>


          <div className="min-w-0 flex-1">

            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">

              <h2 className="font-semibold text-[var(--ink)]">
                {notification.title}
              </h2>

              <time className="shrink-0 text-xs text-[var(--muted)]">
                {formatNotificationTime(
                  notification.created_at
                )}
              </time>
            </div>


            <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
              {notification.sensitive ? (notification.preview || "Sensitive update available. Open the source to view authorized details.") : (notification.preview || notification.message)}
            </p>


            <p className="mt-2 text-xs font-medium text-[var(--accent-text)]">
              {notificationHref(notification) ? "Open details →" : "Account update"}
            </p>
          </div>
        </button>


        <div className="flex shrink-0 items-start gap-1">

          {(!notification.allowed_actions || notification.allowed_actions.includes(notification.is_read ? "MARK_UNREAD" : "MARK_READ")) && (notification.is_read ? (
            <button
              type="button"
              onClick={onUnread}
              title="Mark unread"
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-800"
            >
              <MailOpen
                size={17}
              />
            </button>
          ) : (
            <button
              type="button"
              onClick={onRead}
              title="Mark read"
              className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-800"
            >
              <CheckCheck
                size={17}
              />
            </button>
          ))}


          {(!notification.allowed_actions || notification.allowed_actions.includes("DELETE")) && <button
            type="button"
            onClick={onDelete}
            title="Delete notification"
            className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 size={17} />
          </button>}
        </div>
      </div>
    </article>
  );
}


function SummaryCard({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-gray-500">
        {label}
      </p>

      <p className="mt-2 text-3xl font-bold text-gray-950">
        {value}
      </p>
    </div>
  );
}


function NotificationLoading() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4].map(
        (item) => (
          <div
            key={item}
            className="h-28 animate-pulse rounded-xl bg-gray-200"
          />
        )
      )}
    </div>
  );
}


function formatNotificationTime(
  value: string
) {
  const date =
    new Date(value);

  const difference =
    Date.now() -
    date.getTime();

  const minutes =
    Math.floor(
      difference / 60_000
    );

  if (minutes < 1) {
    return "Just now";
  }

  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours =
    Math.floor(
      minutes / 60
    );

  if (hours < 24) {
    return `${hours}h ago`;
  }

  return date.toLocaleDateString();
}
